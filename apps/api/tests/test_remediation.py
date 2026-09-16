"""Regression coverage for the final PR #4 remediation boundaries."""

from __future__ import annotations

from types import SimpleNamespace

from sqlalchemy import select
from sqlalchemy.orm import Session

from arie_sentinel.config import Settings
from arie_sentinel.models.core import EntityCandidate
from arie_sentinel.models.enums import (
    CompletenessState,
    PersonEvidenceStatus,
    RelationshipState,
    ScreeningState,
    SourceClass,
)
from arie_sentinel.models.evidence import Evidence, Source
from arie_sentinel.providers import fixtures
from arie_sentinel.providers.base import DomainRecord, ProviderUnavailable, RetrievedPage, WebResult
from arie_sentinel.providers.factory import build_providers
from arie_sentinel.services.investigations import (
    _company_screening_subject,
    _corroborate_contact,
    _run_public_intelligence,
    _run_screening,
    create_investigation,
)
from arie_sentinel.services.reports import screening_summary


def _create(db: Session, *, case_context: dict[str, str] | None = None):
    investigation = create_investigation(
        db,
        company_label="Example Public Company Ltd",
        contact_label="Example Public Person",
        actor="analyst@example.test",
        case_context=case_context,
    )
    db.flush()
    return investigation


def test_live_mode_never_constructs_fixture_providers(monkeypatch, db: Session) -> None:
    def forbidden():
        raise AssertionError("live mode invoked fixture providers")

    monkeypatch.setattr(fixtures, "build_fixture_providers", forbidden)
    providers = build_providers(Settings(provider_mode="live"))
    investigation = _create(db)

    assert providers.__class__.__name__ == "Providers"
    assert [candidate.label_fragment for candidate in investigation.candidates] == [
        "Example Public Person"
    ]


def test_company_screening_uses_only_established_attributes(db: Session) -> None:
    investigation = _create(db)
    entity = EntityCandidate(
        investigation_id=investigation.investigation_id,
        legal_name="Example Public Company Ltd",
        jurisdiction="gb",
        registry_class="companies_house",
        registry_id="12345678",
        legal_status="Active",
        registered_address=None,
        incorporation_date=None,
        lei="549300PUBLICEXAMPLE1",
        alternative_names=["Example Public Co"],
        provider="test",
        retrieved_at=investigation.created_at,
    )

    subject = _company_screening_subject(investigation, entity)

    assert subject.aliases == ("Example Public Co",)
    assert subject.countries == ("GB",)
    assert subject.identifiers == {
        "registrationNumber": ("12345678",),
        "leiCode": ("549300PUBLICEXAMPLE1",),
    }
    assert subject.birth_dates == ()


def test_company_screening_falls_back_to_name_without_fabrication(db: Session) -> None:
    investigation = _create(db)

    subject = _company_screening_subject(investigation, None)

    assert subject.label == "Example Public Company Ltd"
    assert subject.aliases == ()
    assert subject.countries == ()
    assert subject.birth_dates == ()
    assert subject.identifiers == {}


class _Web:
    def __init__(self, page: RetrievedPage | None) -> None:
        self.page = page

    def search(self, query: str) -> list[WebResult]:
        return [
            WebResult(
                title="Independent publisher result",
                url="https://news.example.test/article",
                excerpt="Search-engine snippet",
                retrieved_at="2026-09-16T00:00:00Z",
                publisher="news.example.test",
            )
        ]

    def retrieve(self, url: str) -> RetrievedPage | None:
        return self.page


class _Domain:
    def __init__(self) -> None:
        self.lookups: list[str] = []

    def lookup(self, domain: str) -> DomainRecord:
        self.lookups.append(domain)
        return DomainRecord(domain=domain, registered_on="2020-01-01")


def test_unretrieved_search_result_is_discovery_only_and_not_rdap_target(db: Session) -> None:
    investigation = _create(db)
    domain = _Domain()
    _run_public_intelligence(
        db,
        investigation,
        SimpleNamespace(web=_Web(None), domain=domain),
    )
    db.flush()

    web_source = db.scalar(select(Source).where(Source.source_class == SourceClass.WEB_PUBLIC))
    assert web_source is not None
    assert web_source.content_hash is None
    assert web_source.captured_by == "adapter:web_search:discovery"
    assert "not evidence" in (web_source.limitations or "")
    assert db.scalar(select(Evidence).where(Evidence.source_id == web_source.source_id)) is None
    assert domain.lookups == []


def test_captured_page_is_evidence_and_rdap_uses_only_claimed_domain(db: Session) -> None:
    investigation = _create(db, case_context={"website": "https://company.example.test/about"})
    domain = _Domain()
    page = RetrievedPage(
        url="https://news.example.test/article",
        content="Captured article body",
        content_hash="a" * 64,
        content_type="text/html",
        retrieved_at="2026-09-16T00:01:00Z",
    )
    _run_public_intelligence(
        db,
        investigation,
        SimpleNamespace(web=_Web(page), domain=domain),
    )
    db.flush()

    web_source = db.scalar(select(Source).where(Source.source_class == SourceClass.WEB_PUBLIC))
    assert web_source is not None and web_source.content_hash == "a" * 64
    evidence = db.scalar(select(Evidence).where(Evidence.source_id == web_source.source_id))
    assert evidence is not None and evidence.excerpt == "Captured article body"
    assert domain.lookups == ["company.example.test"]

    rdap_source = db.scalar(
        select(Source).where(Source.source_class == SourceClass.DOMAIN_REGISTRATION)
    )
    assert rdap_source is not None
    rdap_evidence = db.scalar(select(Evidence).where(Evidence.source_id == rdap_source.source_id))
    assert rdap_evidence is not None
    assert rdap_evidence.observed_value["association_basis"].startswith("supplied case context")
    assert rdap_evidence.observed_value["ownership_proven"] is False


def test_social_profile_is_not_treated_as_company_domain(db: Session) -> None:
    investigation = _create(
        db, case_context={"website": "https://www.linkedin.com/company/example-public"}
    )
    domain = _Domain()

    _run_public_intelligence(
        db,
        investigation,
        SimpleNamespace(web=_Web(None), domain=domain),
    )

    assert domain.lookups == []


class _ZeroScreening:
    def screen(self, subject):
        return []


class _UnavailableScreening:
    def screen(self, subject):
        raise ProviderUnavailable("screening unavailable")


def test_zero_screening_is_distinct_from_provider_unavailable(db: Session) -> None:
    completed = _create(db)
    _run_screening(db, completed, SimpleNamespace(screening=_ZeroScreening()))
    assert completed.screening_state is ScreeningState.NO_MATERIAL_MATCH
    assert screening_summary(completed, []) == (
        "Screening completed and returned no material matches."
    )

    unavailable = _create(db)
    _run_screening(db, unavailable, SimpleNamespace(screening=_UnavailableScreening()))
    assert unavailable.screening_state is None
    assert unavailable.completeness_state is CompletenessState.MATERIAL_SOURCE_UNAVAILABLE
    assert screening_summary(unavailable, []) == (
        "Screening was not completed because a required source was unavailable."
    )


def test_registry_relationship_does_not_overstate_submitted_person_identity(db: Session) -> None:
    investigation = _create(db)
    entity = EntityCandidate(
        investigation_id=investigation.investigation_id,
        legal_name="Example Public Company Ltd",
        jurisdiction="gb",
        registry_class="companies_house",
        registry_id="12345678",
        legal_status="Active",
        registered_address=None,
        incorporation_date=None,
        lei=None,
        alternative_names=[],
        provider="test",
        retrieved_at=investigation.created_at,
    )

    class Registry:
        def discover_officers(self, contact: str, jurisdiction: str, registry_id: str):
            return [{"name": "Example Public Person", "position": "Director"}]

    _corroborate_contact(db, investigation, entity, SimpleNamespace(registry=Registry()))
    candidate = investigation.candidates[0]
    assert candidate.relationship_state is RelationshipState.VERIFIED
    assert candidate.person_evidence_status is PersonEvidenceStatus.LIMITED_EVIDENCE
    assert "does not conclusively verify" in (candidate.match_basis or "")
