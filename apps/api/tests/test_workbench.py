"""Tests for the Counterparty Intelligence Workbench additions.

Covers: the contradiction engine (per-rule + no-false-positive), the investigation
board, the relationship graph, intake context/claims, the new free-provider adapters
(success/timeout/invalid/empty/rate-limit), and the /board and /graph endpoints.
"""

from __future__ import annotations

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from arie_sentinel.models.core import EntityCandidate, Investigation
from arie_sentinel.models.enums import FindingType
from arie_sentinel.models.evidence import Finding
from arie_sentinel.providers.base import (
    ProviderInvalidResponse,
    ProviderRateLimited,
    ProviderUnavailable,
)
from arie_sentinel.providers.gdelt import GdeltNewsProvider
from arie_sentinel.providers.sec_edgar import SecEdgarProvider
from arie_sentinel.services.board import build_board
from arie_sentinel.services.contradictions import (
    ContradictionContext,
    DomainFact,
    evaluate,
)
from arie_sentinel.services.graph import build_graph
from arie_sentinel.services.investigations import (
    create_investigation,
    resolve_entity,
    run_discovery,
    run_enrichment,
)

ANALYST = "analyst@example.test"
ANALYST_HEADERS = {"X-Dev-Role": "analyst"}


def _client(handler: object) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))  # type: ignore[arg-type]


def _process(
    db: Session, company: str, contact: str = "", claims: dict | None = None
) -> Investigation:
    inv = create_investigation(
        db, company_label=company, contact_label=contact, actor=ANALYST, claims=claims
    )
    db.flush()
    run_discovery(db, inv.investigation_id)
    db.flush()
    candidate = db.scalar(
        select(EntityCandidate).where(EntityCandidate.investigation_id == inv.investigation_id)
    )
    assert candidate is not None
    resolve_entity(db, inv, candidate, actor=ANALYST, rationale="Registry identifier checked")
    db.flush()
    run_enrichment(db, inv.investigation_id, candidate.entity_candidate_id)
    db.flush()
    return inv


# --- Contradiction engine (pure) -----------------------------------------------------


def test_operating_since_before_incorporation_is_contradiction() -> None:
    ctx = ContradictionContext(
        claims={"operating_since_year": 2008}, registry_incorporation_date="2023-05-09"
    )
    keys = {r.key for r in evaluate(ctx)}
    assert "operating_since_before_incorporation" in keys


def test_registration_and_jurisdiction_mismatch() -> None:
    ctx = ContradictionContext(
        claims={"registration_number": "GB-OLD-0001", "jurisdiction": "SG"},
        registry_id="14750888",
        registry_jurisdiction="GB",
    )
    keys = {r.key for r in evaluate(ctx)}
    assert "registration_number_mismatch" in keys
    assert "jurisdiction_mismatch" in keys


def test_contact_email_and_licence_and_domain_age() -> None:
    ctx = ContradictionContext(
        claims={
            "operating_since_year": 2008,
            "contact_email": "person@other-domain.example",
            "website": "https://company.example.test",
            "licence": "FCA authorised",
        },
        domains=(DomainFact(domain="company.example.test", registered_on="2024-06-01"),),
        has_authoritative_regulator_source=False,
    )
    keys = {r.key for r in evaluate(ctx)}
    assert "contact_email_domain_mismatch" in keys
    assert "licence_not_independently_established" in keys
    assert "domain_age_vs_operating_history" in keys


def test_no_false_contradiction_when_data_is_unavailable() -> None:
    # Claims present but no discovered facts -> no contradictions manufactured.
    ctx = ContradictionContext(
        claims={"operating_since_year": 2008, "registration_number": "X", "jurisdiction": "GB"}
    )
    assert evaluate(ctx) == []


def test_no_contradiction_when_claims_match_evidence() -> None:
    ctx = ContradictionContext(
        claims={
            "operating_since_year": 2023,
            "registration_number": "14750888",
            "jurisdiction": "GB",
        },
        registry_id="14750888",
        registry_jurisdiction="GB",
        registry_incorporation_date="2023-05-09",
    )
    assert evaluate(ctx) == []


# --- Contradiction engine end-to-end (Zenith demo) -----------------------------------


def test_zenith_demo_surfaces_contradictions(db: Session) -> None:
    inv = _process(
        db,
        "Zenith Global Traders Ltd",
        contact="Robert Vance",
        claims={
            "operating_since_year": 2008,
            "registration_number": "GB-OLD-0001",
            "jurisdiction": "GB",
            "website": "https://zenith-global.example.test",
            "contact_email": "robert@zenith-holdings-different.example",
            "licence": "FCA authorised",
        },
    )
    findings = db.scalars(
        select(Finding).where(Finding.investigation_id == inv.investigation_id)
    ).all()
    titles = {f.title for f in findings}
    assert "Claimed operating history predates registry incorporation" in titles
    assert "Supplied registration number does not match resolved entity" in titles
    assert "Contact email domain differs from the company domain" in titles
    assert "Regulatory/licence claim not independently established" in titles
    # No jurisdiction contradiction (claim matches registry).
    assert "Claimed jurisdiction conflicts with registry identity" not in titles
    contradiction_findings = [
        f
        for f in findings
        if f.finding_type
        in {
            FindingType.CONTRADICTION,
            FindingType.INCONSISTENCY,
            FindingType.ANOMALY,
            FindingType.UNVERIFIED_CLAIM,
        }
    ]
    assert len(contradiction_findings) >= 4


def test_clean_case_has_no_contradictions(db: Session) -> None:
    inv = _process(db, "Meridian Energy Supplies Ltd")
    findings = db.scalars(
        select(Finding).where(Finding.investigation_id == inv.investigation_id)
    ).all()
    assert [f for f in findings if f.finding_type is FindingType.CONTRADICTION] == []


# --- Board ---------------------------------------------------------------------------


def test_board_reports_confirmed_identity_and_actions(db: Session) -> None:
    inv = _process(
        db,
        "Zenith Global Traders Ltd",
        contact="Robert Vance",
        claims={
            "operating_since_year": 2008,
            "registration_number": "GB-OLD-0001",
        },
    )
    rows = {r.key: r for r in build_board(db, inv)}
    assert rows["legal_identity"].state == "CONFIRMED"
    assert rows["contradictions"].action_required is True
    assert rows["analyst_actions"].action_required is True
    # every row carries an explicit evidence/screening state token
    assert all(r.state for r in rows.values())


def test_board_marks_source_unavailable(db: Session) -> None:
    inv = create_investigation(
        db, company_label="Unknown Example Holdings", contact_label="", actor=ANALYST
    )
    db.flush()
    run_discovery(db, inv.investigation_id)
    db.flush()
    rows = {r.key: r for r in build_board(db, inv)}
    assert rows["legal_identity"].state == "SOURCE_UNAVAILABLE"


# --- Graph ---------------------------------------------------------------------------


def test_graph_has_provenance_and_no_unsupported_edges(db: Session) -> None:
    inv = _process(db, "Pacific Energy Procurement Ltd", contact="Daniel Kim")
    graph = build_graph(db, inv)
    node_ids = {n.id for n in graph.nodes}
    assert "company:subject" in node_ids
    # Daniel Kim is a verified officer for Pacific -> a person node + edge exists.
    assert any(n.type == "Person" for n in graph.nodes)
    assert graph.edges, "expected at least one relationship edge"
    for edge in graph.edges:
        assert edge.source in node_ids and edge.target in node_ids
        assert edge.basis, "every edge must carry a provenance basis"
        assert edge.state


# --- Endpoints -----------------------------------------------------------------------


def test_board_and_graph_endpoints(client: TestClient) -> None:
    created = client.post(
        "/investigations",
        json={
            "company_label": "Zenith Global Traders Ltd",
            "contact_label": "Robert Vance",
            "investigation_context": "Prospective client",
            "claims": {"operating_since_year": 2008, "registration_number": "GB-OLD-0001"},
        },
        headers=ANALYST_HEADERS,
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["investigation_context"] == "Prospective client"
    inv_id = body["investigation_id"]

    from arie_sentinel.db import SessionLocal
    from arie_sentinel.jobs.worker import run_pending_jobs

    session = SessionLocal()
    try:
        run_pending_jobs(session)  # discovery
    finally:
        session.close()
    discovered = client.get(f"/investigations/{inv_id}", headers=ANALYST_HEADERS).json()
    client.post(
        f"/investigations/{inv_id}/resolve-entity",
        json={
            "candidate_id": discovered["entity_candidates"][0]["entity_candidate_id"],
            "rationale": "Registry identifier checked",
        },
        headers=ANALYST_HEADERS,
    )
    session = SessionLocal()
    try:
        run_pending_jobs(session)  # enrichment + contradictions
    finally:
        session.close()

    board = client.get(f"/investigations/{inv_id}/board", headers=ANALYST_HEADERS)
    assert board.status_code == 200, board.text
    board_body = board.json()
    assert board_body["investigation_context"] == "Prospective client"
    keys = {row["key"] for row in board_body["rows"]}
    assert {"legal_identity", "sanctions", "contradictions", "analyst_actions"}.issubset(keys)

    graph = client.get(f"/investigations/{inv_id}/graph", headers=ANALYST_HEADERS)
    assert graph.status_code == 200, graph.text
    graph_body = graph.json()
    assert any(n["id"] == "company:subject" for n in graph_body["nodes"])
    assert all(e["basis"] for e in graph_body["edges"])


# --- Free-provider adapters ----------------------------------------------------------


def test_sec_edgar_success_and_empty() -> None:
    provider = SecEdgarProvider("https://efts.example.test")
    provider.client = _client(
        lambda request: httpx.Response(
            200,
            json={
                "hits": {
                    "hits": [{"_source": {"display_names": ["ACME CORP (CIK 0000001)"], "cik": 1}}]
                }
            },
            request=request,
        )
    )
    records = provider.search_company("ACME")
    assert records and records[0].cik == "1"

    provider.client = _client(
        lambda request: httpx.Response(200, json={"hits": {"hits": []}}, request=request)
    )
    assert provider.search_company("Nobody") == []


def test_sec_edgar_failure_modes() -> None:
    provider = SecEdgarProvider("https://efts.example.test")

    def timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    provider.client = _client(timeout)
    with pytest.raises(ProviderUnavailable):
        provider.search_company("ACME")

    provider.client = _client(lambda request: httpx.Response(429, request=request))
    with pytest.raises(ProviderRateLimited):
        provider.search_company("ACME")

    provider.client = _client(
        lambda request: httpx.Response(200, json={"hits": "bad"}, request=request)
    )
    with pytest.raises(ProviderInvalidResponse):
        provider.search_company("ACME")


def test_gdelt_success_empty_and_invalid() -> None:
    provider = GdeltNewsProvider("https://gdelt.example.test")
    provider.client = _client(
        lambda request: httpx.Response(
            200,
            json={
                "articles": [
                    {
                        "url": "https://news.example/a",
                        "title": "Headline",
                        "seendate": "20260101T000000Z",
                        "domain": "news.example",
                    }
                ]
            },
            request=request,
        )
    )
    results = provider.search("Example Company")
    assert len(results) == 1
    assert results[0].publisher == "news.example"
    assert results[0].excerpt == ""  # discovery metadata only, never authoritative

    provider.client = _client(lambda request: httpx.Response(200, json={}, request=request))
    assert provider.search("Example Company") == []

    provider.client = _client(
        lambda request: httpx.Response(200, json={"articles": "bad"}, request=request)
    )
    with pytest.raises(ProviderInvalidResponse):
        provider.search("Example Company")


# --- PR #8 review remediation ---------------------------------------------------------

from types import SimpleNamespace as _NS  # noqa: E402

from arie_sentinel.models.core import PersonCandidate  # noqa: E402
from arie_sentinel.models.enums import (  # noqa: E402
    ExtractionConfidence,
    RelationshipState,
    SourceClass,
)
from arie_sentinel.models.evidence import Evidence, Source  # noqa: E402
from arie_sentinel.providers.base import ScreeningSubject  # noqa: E402
from arie_sentinel.providers.companies_house import CompaniesHouseProvider  # noqa: E402
from arie_sentinel.providers.gleif import GleifProvider  # noqa: E402
from arie_sentinel.providers.sanctions import (  # noqa: E402
    OfficialSanctionsProvider,
    SanctionedEntity,
)
from arie_sentinel.services.contradictions import (  # noqa: E402
    REGULATOR_LICENCE_LICENSE_CLASS,
    build_context,
)
from arie_sentinel.services.investigations import (  # noqa: E402
    _claimed_company_domains,
    _run_public_intelligence,
    _run_supplementary_sources,
)


class _FakeDomain:
    def __init__(self) -> None:
        self.lookups: list[str] = []

    def lookup(self, domain: str):
        self.lookups.append(domain)
        from arie_sentinel.providers.base import DomainRecord

        return DomainRecord(domain=domain, registered_on="2024-01-01")


class _FakeWeb:
    def search(self, query: str):
        return []

    def retrieve(self, url: str):
        return None


# BLOCKER 1 — a website supplied through the live intake claims path drives RDAP.


def test_intake_claim_website_is_a_claimed_domain(db: Session) -> None:
    inv = create_investigation(
        db,
        company_label="Vantar - Castellan",
        contact_label="",
        actor=ANALYST,
        claims={"website": "https://acme-live.example.test"},
    )
    db.flush()
    domains = _claimed_company_domains(inv)
    assert "acme-live.example.test" in domains


def test_intake_claim_website_triggers_domain_enrichment(db: Session) -> None:
    inv = create_investigation(
        db,
        company_label="Vantar - Castellan",
        contact_label="",
        actor=ANALYST,
        claims={"website": "https://acme-live.example.test"},
    )
    db.flush()
    domain = _FakeDomain()
    _run_public_intelligence(db, inv, _NS(web=_FakeWeb(), domain=domain))
    assert domain.lookups == ["acme-live.example.test"]


# MAJOR 6 — a corporate registry / generic government source must NOT satisfy a licence claim.


def test_public_government_source_does_not_establish_licence(db: Session) -> None:
    inv = create_investigation(
        db, company_label="Vantar - Castellan", contact_label="", actor=ANALYST
    )
    db.flush()
    src = Source(
        investigation_id=inv.investigation_id,
        source_class=SourceClass.CORPORATE_REGISTRY,
        title="Registry candidate: Example",
        retrieved_at=inv.created_at,
        captured_by="fixture:public_registry_citation",
        limitations="registry",
        license_class="public-government-source",
    )
    db.add(src)
    db.flush()
    db.add(
        Evidence(
            source_id=src.source_id,
            observed_value={"registry_id": "X1", "legal_name": "Example"},
            extracted_by="x",
            extraction_confidence=ExtractionConfidence.AUTHORITATIVE,
        )
    )
    db.flush()
    candidate = EntityCandidate(
        investigation_id=inv.investigation_id,
        legal_name="Example",
        jurisdiction="GB",
        registry_class="companies_house",
        registry_id="X1",
        legal_status="Active",
        registered_address=None,
        incorporation_date=None,
        lei=None,
        alternative_names=[],
        provider="test",
        retrieved_at=inv.created_at,
    )
    db.add(candidate)
    db.flush()
    inv.case_context = {"claims": {"licence": "FCA authorised"}}
    ctx = build_context(db, inv, candidate)
    assert ctx.has_authoritative_regulator_source is False
    keys = {r.key for r in evaluate(ctx)}
    assert "licence_not_independently_established" in keys


def test_regulator_marker_source_does_establish_licence(db: Session) -> None:
    inv = create_investigation(
        db, company_label="Vantar - Castellan", contact_label="", actor=ANALYST
    )
    db.flush()
    src = Source(
        investigation_id=inv.investigation_id,
        source_class=SourceClass.OFFICIAL_PUBLICATION,
        title="Regulator register",
        retrieved_at=inv.created_at,
        captured_by="adapter:regulator",
        limitations="regulator licence verification",
        license_class=REGULATOR_LICENCE_LICENSE_CLASS,
    )
    db.add(src)
    db.flush()
    db.add(
        Evidence(
            source_id=src.source_id,
            observed_value={"licence": "verified"},
            extracted_by="x",
            extraction_confidence=ExtractionConfidence.AUTHORITATIVE,
        )
    )
    db.flush()
    ctx = build_context(db, inv, None)
    assert ctx.has_authoritative_regulator_source is True


# MAJOR 4/5 — faithful relationship-state mapping + evidence-backed provenance.


def _candidate(inv: Investigation, name: str, state: RelationshipState) -> PersonCandidate:
    return PersonCandidate(
        investigation_id=inv.investigation_id,
        label_fragment=name,
        relationship_state=state,
        created_by="system",
    )


def test_graph_preserves_relationship_states(db: Session) -> None:
    inv = create_investigation(
        db, company_label="Vantar - Castellan", contact_label="", actor=ANALYST
    )
    db.flush()
    db.add_all(
        [
            _candidate(inv, "Corr Person", RelationshipState.CORROBORATED),
            _candidate(inv, "Self Person", RelationshipState.SELF_ASSERTED),
            _candidate(inv, "Unv Person", RelationshipState.UNVERIFIED),
            _candidate(inv, "Contra Person", RelationshipState.CONTRADICTED),
        ]
    )
    db.flush()
    db.refresh(inv)
    graph = build_graph(db, inv)
    by_state = {e.state for e in graph.edges}
    assert {"CORROBORATED", "CLAIMED", "UNVERIFIED", "CONTRADICTED"}.issubset(by_state)
    # None of these claim-only relationships were collapsed to a directorship.
    assert all(e.type != "DIRECTOR_OF" for e in graph.edges)
    # A claim-only relationship legitimately carries no external source id.
    for edge in graph.edges:
        if edge.state in {"CLAIMED", "UNVERIFIED", "CONTRADICTED"}:
            assert edge.source_ids == []


def test_verified_officer_edge_carries_provenance(db: Session) -> None:
    inv = _process(db, "Pacific Energy Procurement Ltd", contact="Daniel Kim")
    graph = build_graph(db, inv)
    officer_edges = [e for e in graph.edges if e.type in {"OFFICER_OF", "DIRECTOR_OF"}]
    assert officer_edges
    assert all(e.source_ids for e in officer_edges)  # evidence-backed edges have provenance


# ISSUE 8 — SEC/GDELT actually consumed by enrichment (with mocked providers).


class _FakeGdelt:
    def search(self, query: str):
        from arie_sentinel.providers.base import WebResult

        return [
            WebResult(
                title="Lead",
                url="https://news.example/x",
                excerpt="",
                retrieved_at="2026-09-18T00:00:00Z",
                publisher="news.example",
                published_at="20260101T000000Z",
            )
        ]


class _FakeSec:
    def search_company(self, name: str):
        from arie_sentinel.providers.sec_edgar import EdgarRecord

        return [EdgarRecord(name="ACME CORP", cik="1", tickers=("ACME",))]


def test_supplementary_sources_consume_gdelt_and_sec(db: Session) -> None:
    inv = create_investigation(
        db, company_label="Vantar - Castellan", contact_label="", actor=ANALYST
    )
    db.flush()
    cp, _ = __import__(
        "arie_sentinel.services.investigations", fromlist=["get_or_create_counterparty"]
    ).get_or_create_counterparty(
        db,
        EntityCandidate(
            investigation_id=inv.investigation_id,
            legal_name="ACME",
            jurisdiction="US-DE",
            registry_class="us_state_registry",
            registry_id="US-1",
            legal_status="Active",
            registered_address=None,
            incorporation_date=None,
            lei=None,
            alternative_names=[],
            provider="test",
            retrieved_at=inv.created_at,
        ),
    )
    inv.counterparty_id = cp.counterparty_id
    inv.counterparty = cp
    db.flush()
    _run_supplementary_sources(db, inv, _NS(news=_FakeGdelt(), sec=_FakeSec()))
    db.flush()
    titles = [
        s.title
        for s in db.scalars(select(Source).where(Source.investigation_id == inv.investigation_id))
    ]
    assert any(t.startswith("SEC EDGAR:") for t in titles)
    assert "Lead" in titles  # GDELT discovery lead retained


# ISSUE 9 — Companies House adapter behaviour (mocked).


def test_companies_house_success_and_failures() -> None:
    provider = CompaniesHouseProvider("free-key", "https://ch.example.test")
    provider.client = _client(
        lambda request: httpx.Response(
            200,
            json={
                "items": [
                    {"title": "ACME LTD", "company_number": "12345678", "company_status": "active"}
                ]
            },
            request=request,
        )
    )
    rows = provider.search_company("ACME")
    assert rows and rows[0].registry_id == "12345678"

    provider.client = _client(
        lambda request: httpx.Response(200, json={"items": []}, request=request)
    )
    assert provider.search_company("Nobody") == []

    provider.client = _client(lambda request: httpx.Response(401, request=request))
    with pytest.raises(ProviderUnavailable):
        provider.search_company("ACME")

    provider.client = _client(lambda request: httpx.Response(429, request=request))
    with pytest.raises(ProviderRateLimited):
        provider.search_company("ACME")

    def timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("t", request=request)

    provider.client = _client(timeout)
    with pytest.raises(ProviderUnavailable):
        provider.search_company("ACME")

    provider.client = _client(
        lambda request: httpx.Response(200, json={"items": "bad"}, request=request)
    )
    with pytest.raises(ProviderInvalidResponse):
        provider.search_company("ACME")


# ISSUE 10 — GLEIF parent/child relationships (mocked); 404 => empty.


def test_gleif_relationships_parse_and_absence() -> None:
    provider = GleifProvider("https://gleif.example.test")

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/direct-parent"):
            return httpx.Response(
                200,
                json={"data": {"attributes": {"lei": "PARENT000000000000LEI"}}},
                request=request,
            )
        if request.url.path.endswith("/direct-children"):
            return httpx.Response(
                200,
                json={"data": [{"attributes": {"lei": "CHILD0000000000000LEI"}}]},
                request=request,
            )
        return httpx.Response(404, request=request)

    provider.client = _client(handler)
    rels = provider.lookup_relationships("SUBJECT00000000000LEI")
    assert rels["parent_lei"] == "PARENT000000000000LEI"
    assert rels["child_leis"] == ["CHILD0000000000000LEI"]

    provider.client = _client(lambda request: httpx.Response(404, request=request))
    empty = provider.lookup_relationships("X")
    assert empty == {"parent_lei": None, "child_leis": []}


# ISSUE 11 — official sanctions matcher: identifier-aware, DOB suppression, fail-closed.

_OFAC = SanctionedEntity(
    name="Victor Lane",
    source_list="OFAC",
    entity_type="person",
    aliases=("V. Lane",),
    birth_dates=("1970-01-01",),
    countries=("RU",),
    identifiers=("PASSPORT-999",),
    profile_id="ofac-1",
)


def test_sanctions_name_match_is_potential_only() -> None:
    provider = OfficialSanctionsProvider([_OFAC])
    hits = provider.screen(ScreeningSubject(label="Victor Lane"))
    assert len(hits) == 1
    assert hits[0].state == "POTENTIAL_MATCH"


def test_sanctions_identifier_match_is_strong_but_still_review() -> None:
    provider = OfficialSanctionsProvider([_OFAC])
    hits = provider.screen(
        ScreeningSubject(label="Unrelated Name", identifiers={"passportNumber": ("PASSPORT-999",)})
    )
    assert len(hits) == 1
    assert hits[0].state == "POTENTIAL_MATCH"
    assert hits[0].score and hits[0].score >= 0.9


def test_sanctions_dob_suppresses_false_positive() -> None:
    provider = OfficialSanctionsProvider([_OFAC])
    hits = provider.screen(ScreeningSubject(label="Victor Lane", birth_dates=("1990-05-05",)))
    assert hits == []  # same name, different DOB -> not a match


def test_sanctions_clean_checked_result_is_empty() -> None:
    provider = OfficialSanctionsProvider([_OFAC])
    assert provider.screen(ScreeningSubject(label="Totally Different Person")) == []


def test_sanctions_unloaded_is_source_unavailable() -> None:
    provider = OfficialSanctionsProvider()  # feeds not loaded
    with pytest.raises(ProviderUnavailable):
        provider.screen(ScreeningSubject(label="Anyone"))
