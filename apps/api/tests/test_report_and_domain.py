"""Domain board semantics (§13) and PDF/HTML relationship provenance (MAJOR 11)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from arie_sentinel.models.enums import EvidenceState, InvestigationState
from arie_sentinel.services.board import build_board
from arie_sentinel.services.investigations import create_investigation
from arie_sentinel.services.reports import build_report_html

ANALYST = "analyst@example.test"


def _domain_row(rows):
    return next(r for r in rows if r.key == "domain_website")


def test_claimed_website_is_claimed_not_corroborated(db: Session) -> None:
    inv = create_investigation(
        db,
        company_label="Testco Ltd",
        contact_label="",
        actor=ANALYST,
        claims={"website": "example.com"},
    )
    db.flush()
    row = _domain_row(build_board(db, inv))
    # A claim alone is never CORROBORATED and carries no source drill-down.
    assert row.state == EvidenceState.CLAIMED.value
    assert "claimed" in row.detail.lower()
    assert "not established" in row.detail.lower()
    assert row.source_ids == []


def test_no_website_claim_is_not_assessed(db: Session) -> None:
    inv = create_investigation(db, company_label="Testco Ltd", contact_label="", actor=ANALYST)
    db.flush()
    row = _domain_row(build_board(db, inv))
    assert row.state == EvidenceState.NOT_ASSESSED.value


def test_report_shows_relationship_provenance_table(db: Session) -> None:
    inv = create_investigation(
        db, company_label="Testco Ltd", contact_label="Jane Roe", actor=ANALYST
    )
    inv.investigation_state = InvestigationState.COMPLETED
    db.flush()
    html = build_report_html(db, inv)
    assert "Relationships (provenance)" in html
    for header in ("From", "Relationship", "To", "State", "Basis"):
        assert f"<th>{header}</th>" in html
    # The supplied contact is a claim-only edge -> flagged as having no independent source.
    assert "Claim only" in html
