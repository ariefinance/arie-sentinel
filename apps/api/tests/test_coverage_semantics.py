"""Evidence-coverage 4-state board logic + supplementary-vs-material source failures."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from sqlalchemy.orm import Session

from arie_sentinel.models.enums import (
    CompletenessState,
    EvidenceState,
    InvestigationState,
    SourceClass,
)
from arie_sentinel.models.evidence import Source
from arie_sentinel.providers.base import ProviderUnavailable
from arie_sentinel.services.board import build_board
from arie_sentinel.services.investigations import (
    _run_supplementary_sources,
    create_investigation,
)

ANALYST = "analyst@example.test"


def _inv(db: Session):
    inv = create_investigation(db, company_label="Testco Ltd", contact_label="", actor=ANALYST)
    db.flush()
    return inv


def _coverage_row(rows):
    return next(r for r in rows if r.key == "evidence_coverage")


def test_coverage_running_is_not_assessed(db: Session) -> None:
    inv = _inv(db)
    inv.investigation_state = InvestigationState.RUNNING
    row = _coverage_row(build_board(db, inv))
    assert row.state == EvidenceState.NOT_ASSESSED.value


def test_coverage_completed_zero_evidence_is_unverified_not_confirmed(db: Session) -> None:
    inv = _inv(db)
    inv.investigation_state = InvestigationState.COMPLETED
    inv.completeness_state = CompletenessState.COMPLETE_WITH_LIMITATIONS
    row = _coverage_row(build_board(db, inv))
    # Zero collected sources with zero errors is NOT "confirmed coverage".
    assert row.state == EvidenceState.UNVERIFIED.value


def test_coverage_completed_with_evidence_is_reported(db: Session) -> None:
    inv = _inv(db)
    inv.investigation_state = InvestigationState.COMPLETED
    db.add(
        Source(
            investigation_id=inv.investigation_id,
            source_class=SourceClass.WEB_PUBLIC,
            title="A source",
            retrieved_at=datetime.now(UTC),
            captured_by="adapter:web_retrieval",
            limitations="x",
            license_class="linked-public-source",
        )
    )
    db.flush()
    row = _coverage_row(build_board(db, inv))
    assert row.state == EvidenceState.REPORTED.value


def test_coverage_material_source_unavailable(db: Session) -> None:
    inv = _inv(db)
    inv.investigation_state = InvestigationState.COMPLETED
    inv.completeness_state = CompletenessState.MATERIAL_SOURCE_UNAVAILABLE
    row = _coverage_row(build_board(db, inv))
    assert row.state == EvidenceState.SOURCE_UNAVAILABLE.value


class _FailNews:
    def search(self, query: str):
        raise ProviderUnavailable("gdelt down")


def test_supplementary_gdelt_failure_is_limitation_not_material(db: Session) -> None:
    inv = _inv(db)
    inv.completeness_state = None
    _run_supplementary_sources(db, inv, SimpleNamespace(news=_FailNews()))
    # A supplementary (discovery) outage never downgrades the whole case to material.
    assert inv.completeness_state is CompletenessState.COMPLETE_WITH_LIMITATIONS


def test_supplementary_failure_does_not_overwrite_material(db: Session) -> None:
    inv = _inv(db)
    inv.completeness_state = CompletenessState.MATERIAL_SOURCE_UNAVAILABLE
    _run_supplementary_sources(db, inv, SimpleNamespace(news=_FailNews()))
    assert inv.completeness_state is CompletenessState.MATERIAL_SOURCE_UNAVAILABLE
