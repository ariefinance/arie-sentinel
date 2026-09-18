"""Regression coverage for the pre-management-demo remediation (B1, B2, M1, M2, M3).

Each block maps to a Claude review finding:
- B1: fixture data must never leak to unsupported near-match names.
- B2: analyst rationale is analyst-authored and server-validated.
- M1: fixture/public summaries carry honest non-live provenance.
- M2: the report retains case type, non-live marker, source limitations, and the
       analyst resolution actor/rationale/timestamp.
- M3: the worker survives cycle errors, terminal job failure surfaces on the
       investigation, and malformed provider responses are source-unavailable.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from arie_sentinel import demo_dataset
from arie_sentinel.db import SessionLocal
from arie_sentinel.demo_dataset import (
    DEMO_CASES,
    FICTIONAL_TEST_CASE,
    SEED_CASE_LABELS,
    SEED_CONTACTS,
    iter_seed_cases,
    lookup_demo_case,
    normalise_label,
)
from arie_sentinel.jobs import worker
from arie_sentinel.jobs.worker import run_pending_jobs
from arie_sentinel.models.core import Counterparty, EntityCandidate, Investigation
from arie_sentinel.models.enums import (
    AuditAction,
    CompletenessState,
    InvestigationState,
    JobStatus,
    SourceClass,
)
from arie_sentinel.models.evidence import Evidence, ScreeningResult, Source
from arie_sentinel.models.ops import AuditEvent, Job
from arie_sentinel.providers import DemoDatasetUnsupported
from arie_sentinel.providers.base import ProviderInvalidResponse
from arie_sentinel.providers.fixtures import build_fixture_providers
from arie_sentinel.schemas import ResolveEntityRequest, ReviewRequest
from arie_sentinel.services.investigations import (
    _run_screening,
    create_investigation,
    resolve_entity,
    run_discovery,
    run_enrichment,
)
from arie_sentinel.services.reports import build_report_html

ANALYST = "analyst@example.test"
ANALYST_HEADERS = {"X-Dev-Role": "analyst"}


def _drain_jobs() -> None:
    session = SessionLocal()
    try:
        run_pending_jobs(session)
    finally:
        session.close()


def _process(db: Session, company: str, contact: str = "") -> Investigation:
    """Create -> discover -> resolve -> enrich a supported case, in-process."""
    inv = create_investigation(db, company_label=company, contact_label=contact, actor=ANALYST)
    db.flush()
    run_discovery(db, inv.investigation_id)
    db.flush()
    candidate = db.scalar(
        select(EntityCandidate).where(EntityCandidate.investigation_id == inv.investigation_id)
    )
    assert candidate is not None
    resolve_entity(
        db, inv, candidate, actor=ANALYST, rationale="Registry identifier and jurisdiction checked"
    )
    db.flush()
    run_enrichment(db, inv.investigation_id, candidate.entity_candidate_id)
    db.flush()
    return inv


# --- B1: fixture leakage -------------------------------------------------------------

UNSUPPORTED_NEAR_MATCHES = [
    "Meridian Energy",
    "Atlas Fuels",
    "Pacific Energy",
    "Northstar Petroleum",
    "Orion Energy",
]


@pytest.mark.parametrize("label", UNSUPPORTED_NEAR_MATCHES)
def test_unsupported_near_match_raises_and_returns_no_fixture(label: str) -> None:
    with pytest.raises(DemoDatasetUnsupported, match="management-demo dataset"):
        build_fixture_providers().registry.discover_candidates(label)


@pytest.mark.parametrize("label", UNSUPPORTED_NEAR_MATCHES)
def test_unsupported_near_match_creates_no_fixture_records(db: Session, label: str) -> None:
    inv = create_investigation(db, company_label=label, contact_label="", actor=ANALYST)
    db.flush()
    run_discovery(db, inv.investigation_id)
    db.flush()

    assert inv.investigation_state is InvestigationState.SOURCE_UNAVAILABLE
    assert inv.company_identity_status is None
    assert inv.case_type is None
    assert "Not available in the management-demo dataset" in (inv.clarification_reason or "")
    # No fictional counterparty, no candidates, no screening clearance, no evidence.
    assert inv.entity_candidates == []
    assert inv.counterparty_id is None
    assert inv.screening_state is None
    assert db.scalar(select(func.count()).select_from(EntityCandidate)) == 0
    assert db.scalar(select(func.count()).select_from(Counterparty)) == 0
    assert db.scalar(select(func.count()).select_from(ScreeningResult)) == 0
    assert db.scalar(select(func.count()).select_from(Evidence)) == 0


@pytest.mark.parametrize(
    "label,expected",
    [
        ("Meridian Energy Supplies Ltd", 1),
        ("Northstar Petroleum Trading", 1),
        ("Atlas Global Fuels", 1),
        ("Orion Petro Trading", 3),
        ("ARIE Finance", 1),
        ("ARIE Finance Ltd", 1),
    ],
)
def test_supported_aliases_still_resolve_exactly(label: str, expected: int) -> None:
    candidates = build_fixture_providers().registry.discover_candidates(label)
    assert len(candidates) == expected


# --- B2: analyst-authored, server-validated rationale --------------------------------


def test_rationale_min_length_is_server_enforced() -> None:
    with pytest.raises(ValidationError):
        ReviewRequest(disposition="FALSE_POSITIVE", rationale="ok")
    with pytest.raises(ValidationError):
        ResolveEntityRequest(candidate_id=uuid.uuid4(), rationale="short")
    # A proportionate rationale is accepted.
    ReviewRequest(disposition="FALSE_POSITIVE", rationale="Identifiers do not match")
    ResolveEntityRequest(candidate_id=uuid.uuid4(), rationale="Registry identifier checked")


def test_resolution_rationale_is_persisted_exactly_as_entered(db: Session) -> None:
    inv = create_investigation(
        db, company_label="Vantar - Castellan", contact_label="", actor=ANALYST
    )
    db.flush()
    run_discovery(db, inv.investigation_id)
    db.flush()
    candidate = inv.entity_candidates[0]
    rationale = "Distinctive analyst-authored reasoning 20260917"
    resolve_entity(db, inv, candidate, actor=ANALYST, rationale=rationale)
    db.flush()
    event = db.scalar(
        select(AuditEvent).where(
            AuditEvent.investigation_id == inv.investigation_id,
            AuditEvent.action == AuditAction.RESOLVE_IDENTITY,
        )
    )
    assert event is not None
    assert event.rationale == rationale


def test_api_rejects_short_resolution_rationale(client: TestClient) -> None:
    created = client.post(
        "/investigations",
        json={"company_label": "Vantar - Castellan", "contact_label": "Jordan Rivera"},
        headers=ANALYST_HEADERS,
    ).json()
    _drain_jobs()
    discovered = client.get(
        f"/investigations/{created['investigation_id']}", headers=ANALYST_HEADERS
    ).json()
    candidate_id = discovered["entity_candidates"][0]["entity_candidate_id"]
    resp = client.post(
        f"/investigations/{created['investigation_id']}/resolve-entity",
        json={"candidate_id": candidate_id, "rationale": "ok"},
        headers=ANALYST_HEADERS,
    )
    assert resp.status_code == 422


def test_frontend_has_no_hardcoded_analyst_rationale() -> None:
    web_src = Path(__file__).resolve().parents[2] / "web" / "src"
    banned = [
        "Analyst reviewed the identifiers",
        "Analyst corroborated the matched identifiers",
        "Analyst reviewed the linked evidence and confirms",
        "Analyst reviewed the linked evidence and dismisses",
        "Selected after reviewing registry identifiers",
    ]
    offenders = []
    for path in web_src.rglob("*.tsx"):
        text = path.read_text(encoding="utf-8")
        for phrase in banned:
            if phrase in text:
                offenders.append(f"{path.name}: {phrase}")
    assert offenders == [], offenders


# --- M1: honest non-live provenance --------------------------------------------------


def test_public_validation_web_summaries_are_curated_not_live(db: Session) -> None:
    inv = _process(db, "ARIE Finance")
    web_sources = db.scalars(
        select(Source).where(
            Source.investigation_id == inv.investigation_id,
            Source.source_class == SourceClass.WEB_PUBLIC,
        )
    ).all()
    assert web_sources
    for source in web_sources:
        assert source.captured_by == "fixture:curated_summary"
        assert source.captured_by != "adapter:web_retrieval"
        assert "not a live" in (source.limitations or "").lower()
    # The public registry citation is not labelled as a live adapter capture.
    registry = db.scalar(
        select(Source).where(
            Source.investigation_id == inv.investigation_id,
            Source.source_class == SourceClass.CORPORATE_REGISTRY,
        )
    )
    assert registry is not None
    assert registry.captured_by == "fixture:public_registry_citation"


def test_fictional_web_summaries_are_curated_not_live(db: Session) -> None:
    inv = _process(db, "Meridian Energy Supplies Ltd")
    web_sources = db.scalars(
        select(Source).where(
            Source.investigation_id == inv.investigation_id,
            Source.source_class == SourceClass.WEB_PUBLIC,
        )
    ).all()
    assert web_sources
    for source in web_sources:
        assert source.captured_by == "fixture:curated_summary"
        assert "no live page was retrieved" in (source.limitations or "")


# --- M2: report retains case type, marker, limitations, resolution audit -------------


def test_fictional_report_html_marks_non_live_and_shows_resolution(db: Session) -> None:
    inv = create_investigation(
        db, company_label="Meridian Energy Supplies Ltd", contact_label="", actor=ANALYST
    )
    db.flush()
    run_discovery(db, inv.investigation_id)
    db.flush()
    candidate = inv.entity_candidates[0]
    rationale = "Fictional registry identifier verified for demo 20260917"
    resolve_entity(db, inv, candidate, actor="manager@example.test", rationale=rationale)
    db.flush()
    run_enrichment(db, inv.investigation_id, candidate.entity_candidate_id)
    db.flush()

    html = build_report_html(db, inv)
    assert "Fictional Test Case" in html
    assert "MANAGEMENT DEMO · FICTIONAL TEST DATA · NON-LIVE" in html
    assert "Analyst resolution rationale" in html
    assert rationale in html
    assert "manager@example.test" in html
    assert "Limitations" in html  # sources table column header
    assert "Fictional screening scenario completed with no material fixture matches." in html


def test_public_validation_report_html_marks_non_live_screening(db: Session) -> None:
    inv = _process(db, "ARIE Finance")
    html = build_report_html(db, inv)
    assert "Public Validation Case" in html
    assert "MANAGEMENT DEMO · PUBLIC VALIDATION · NON-LIVE SCREENING" in html
    assert "Live sanctions/PEP screening was not performed" in html
    assert "Limitations" in html


# --- M3: worker resilience -----------------------------------------------------------


def test_worker_loop_survives_a_cycle_error(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"n": 0}

    def flaky(session: Session) -> int:
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("simulated transient DB error in polling")
        return 0

    monkeypatch.setattr(worker, "run_pending_jobs", flaky)
    # The first cycle raises; the loop must continue and run a second cycle.
    worker.run_worker(poll_interval=0, error_backoff=0, max_cycles=2)
    assert calls["n"] == 2


def test_terminal_job_failure_marks_investigation_failed(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    inv = create_investigation(
        db, company_label="Vantar - Castellan", contact_label="Jordan Rivera", actor=ANALYST
    )
    db.commit()
    assert run_pending_jobs(db) == 1  # discovery
    db.refresh(inv)
    candidate = db.scalar(
        select(EntityCandidate).where(EntityCandidate.investigation_id == inv.investigation_id)
    )
    resolve_entity(db, inv, candidate, actor=ANALYST, rationale="Registry identifier checked")
    db.commit()

    def boom(*args: object, **kwargs: object) -> None:
        raise RuntimeError("simulated permanent enrichment failure")

    monkeypatch.setattr(worker, "run_enrichment", boom)
    run_pending_jobs(db)  # retries then FAILED
    db.expire_all()

    persisted = db.get(Investigation, inv.investigation_id)
    assert persisted is not None
    assert persisted.investigation_state is InvestigationState.FAILED
    failed_job = db.scalar(
        select(Job).where(
            Job.investigation_id == inv.investigation_id, Job.job_type == "enrichment"
        )
    )
    assert failed_job is not None and failed_job.status is JobStatus.FAILED
    audit = db.scalar(
        select(AuditEvent).where(
            AuditEvent.investigation_id == inv.investigation_id,
            AuditEvent.action == AuditAction.STATE_CHANGE,
            AuditEvent.object_type == "investigation",
            AuditEvent.actor == "worker",
        )
    )
    assert audit is not None
    assert (audit.payload or {}).get("investigation_state") == "FAILED"


class _InvalidScreening:
    def screen(self, subject: object) -> list:
        raise ProviderInvalidResponse("malformed screening payload")


class _InvalidRegistry:
    def discover_candidates(self, company_label: str, jurisdiction: str | None = None) -> list:
        raise ProviderInvalidResponse("malformed registry payload")


def test_invalid_screening_response_is_source_unavailable(db: Session) -> None:
    inv = create_investigation(
        db, company_label="Vantar - Castellan", contact_label="Jordan Rivera", actor=ANALYST
    )
    db.flush()
    _run_screening(db, inv, SimpleNamespace(screening=_InvalidScreening()))
    assert inv.screening_state is None
    assert inv.completeness_state is CompletenessState.MATERIAL_SOURCE_UNAVAILABLE


def test_invalid_registry_response_is_source_unavailable(db: Session) -> None:
    inv = create_investigation(
        db, company_label="Vantar - Castellan", contact_label="", actor=ANALYST
    )
    db.flush()
    run_discovery(db, inv.investigation_id, providers=SimpleNamespace(registry=_InvalidRegistry()))
    assert inv.investigation_state is InvestigationState.SOURCE_UNAVAILABLE
    assert inv.completeness_state is CompletenessState.MATERIAL_SOURCE_UNAVAILABLE


# --- B1 consistency: single-source deployment seeding --------------------------------


def test_every_seeded_company_is_a_canonical_demo_case() -> None:
    seed_cases = iter_seed_cases()
    assert seed_cases  # the demo preloads at least one case
    for company_label, _contact, case_type in seed_cases:
        case = lookup_demo_case(company_label)
        # Company identity + case type originate from the canonical dataset.
        assert case is not None, company_label
        assert case.case_type == case_type
        assert normalise_label(company_label) in DEMO_CASES


def test_seed_contacts_cannot_introduce_a_company() -> None:
    # Contacts are optional scenario metadata; every contact key is a seed case,
    # so a contact entry can never add a company the canonical dataset does not have.
    assert set(SEED_CONTACTS).issubset(set(SEED_CASE_LABELS))


def test_a_canonical_case_becomes_seedable_without_a_second_company_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # "Castellan Trading" is already a supported canonical alias but is not seeded.
    # Listing it in the canonical seed selection is sufficient to seed it — no
    # separate company list to edit, and a contact is optional (company-only).
    monkeypatch.setattr(demo_dataset, "SEED_CASE_LABELS", (*SEED_CASE_LABELS, "Castellan Trading"))
    seeded = {label: (contact, case_type) for label, contact, case_type in iter_seed_cases()}
    assert "Castellan Trading" in seeded
    assert seeded["Castellan Trading"] == ("", FICTIONAL_TEST_CASE)


def test_seeder_cannot_silently_drift_from_canonical_dataset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A seed label that is not a supported canonical case fails loudly rather than
    # seeding an unsupported company.
    monkeypatch.setattr(
        demo_dataset, "SEED_CASE_LABELS", (*SEED_CASE_LABELS, "Unsupported Example Holdings")
    )
    with pytest.raises(RuntimeError, match="not a supported demo case"):
        iter_seed_cases()
