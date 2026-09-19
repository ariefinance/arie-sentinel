"""When free registry coverage is unavailable, safe non-registry checks still run."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from sqlalchemy import select
from sqlalchemy.orm import Session

from arie_sentinel.models.core import Counterparty
from arie_sentinel.models.enums import (
    CompanyIdentityStatus,
    CompletenessState,
    InvestigationState,
    SourceClass,
)
from arie_sentinel.models.evidence import Source
from arie_sentinel.providers.base import (
    DomainRecord,
    RegistryCoverageUnavailable,
    RetrievedPage,
    WebResult,
)
from arie_sentinel.providers.sanctions import OfficialSanctionsProvider
from arie_sentinel.services.investigations import create_investigation, run_discovery

ANALYST = "analyst@example.test"


class _NoCoverageRegistry:
    def discover_candidates(self, company_label: str, jurisdiction: str | None = None):
        raise RegistryCoverageUnavailable("no free registry for this jurisdiction")


class _Web:
    def search(self, query: str):
        return [
            WebResult(
                title="Public mention",
                url="https://news.test/article",
                excerpt="mention",
                retrieved_at=datetime.now(UTC).isoformat(),
                publisher="News",
            )
        ]

    def retrieve(self, url: str):
        return RetrievedPage(
            url=url,
            content="captured",
            content_hash="h",
            content_type="text/html",
            retrieved_at=datetime.now(UTC).isoformat(),
        )


class _Domain:
    def lookup(self, domain: str):
        return DomainRecord(
            domain=domain,
            registered_on="2020-01-01",
            registrar="R",
            source_ref=f"https://rdap.test/{domain}",
        )


def _providers():
    return SimpleNamespace(
        registry=_NoCoverageRegistry(),
        web=_Web(),
        domain=_Domain(),
        screening=OfficialSanctionsProvider(),
    )


def test_no_registry_coverage_still_runs_safe_checks(db: Session) -> None:
    inv = create_investigation(
        db,
        company_label="Obscure Mauritius Trading",
        contact_label="Jane Roe",
        actor=ANALYST,
        claims={"jurisdiction": "MU", "website": "obscure.example"},
    )
    db.flush()
    run_discovery(db, inv.investigation_id, providers=_providers())
    db.flush()

    # Identity is NOT verified and no Counterparty is created.
    assert inv.company_identity_status is CompanyIdentityStatus.NOT_VERIFIED
    assert inv.counterparty_id is None
    assert db.scalar(select(Counterparty)) is None

    # The investigation completes with a coverage limitation, not an empty stop.
    assert inv.investigation_state is InvestigationState.COMPLETED
    assert inv.completeness_state is CompletenessState.COMPLETE_WITH_LIMITATIONS
    assert inv.clarification_reason  # coverage limitation recorded

    # Safe checks ran: RDAP (claimed website) + public-web + screening sources exist.
    source_classes = {
        s.source_class
        for s in db.scalars(select(Source).where(Source.investigation_id == inv.investigation_id))
    }
    assert SourceClass.DOMAIN_REGISTRATION in source_classes
    assert SourceClass.WEB_PUBLIC in source_classes
    assert SourceClass.SANCTIONS_PEP_SCREENING in source_classes

    # Screening ran against an unresolved label; with no cached feeds it cannot clear.
    assert inv.screening_state is None
