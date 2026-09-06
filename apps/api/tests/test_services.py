"""Core spine behaviour: creation, immutability, dedup, ambiguity, discovery, audit."""

from __future__ import annotations

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from arie_sentinel.models.core import Counterparty, Investigation, PersonCandidate
from arie_sentinel.models.enums import (
    AuditAction,
    CompanyIdentityStatus,
    CompletenessState,
    IntakeState,
    InvestigationState,
)
from arie_sentinel.models.ops import AuditEvent
from arie_sentinel.services.investigations import create_investigation, run_discovery

ANALYST = "analyst@example.test"


def _create(db: Session, company: str, contact: str) -> Investigation:
    inv = create_investigation(db, company_label=company, contact_label=contact, actor=ANALYST)
    db.flush()
    return inv


def test_clean_resolved_entity_confirms_and_links(db: Session) -> None:
    inv = _create(db, "Vantar - Castellan", "Jordan Rivera")
    assert inv.intake_state is IntakeState.SUFFICIENT_FOR_DISCOVERY
    run_discovery(db, inv.investigation_id)
    db.flush()
    assert inv.company_identity_status is CompanyIdentityStatus.CONFIRMED
    assert inv.counterparty_id is not None
    assert inv.investigation_state is InvestigationState.COMPLETED


def test_insufficient_intake_blocks_discovery(db: Session) -> None:
    inv = _create(db, "TBD", "Amara")
    assert inv.intake_state is IntakeState.CLARIFICATION_REQUIRED
    # No candidates and no counterparty were manufactured.
    assert inv.candidates == []
    assert inv.counterparty_id is None
    # Discovery is a no-op for a clarification-required intake.
    run_discovery(db, inv.investigation_id)
    db.flush()
    assert inv.company_identity_status is None


def test_ambiguous_is_never_silently_confirmed(db: Session) -> None:
    inv = _create(db, "Vantar Energy Trading", "Jordan Rivera")
    run_discovery(db, inv.investigation_id)
    db.flush()
    assert inv.company_identity_status is CompanyIdentityStatus.AMBIGUOUS
    assert inv.counterparty_id is None


def test_repeated_counterparty_links_not_duplicates(db: Session) -> None:
    a = _create(db, "Vantar - Castellan", "Jordan Rivera")
    b = _create(db, "Vantar - Castellan", "Amara")
    run_discovery(db, a.investigation_id)
    run_discovery(db, b.investigation_id)
    db.flush()
    assert a.counterparty_id is not None
    assert a.counterparty_id == b.counterparty_id
    count = db.scalar(select(func.count()).select_from(Counterparty))
    assert count == 1


def test_source_unavailable_sets_completeness(db: Session) -> None:
    inv = _create(db, "Unavailable Trading", "Jordan Rivera")
    run_discovery(db, inv.investigation_id)
    db.flush()
    assert inv.investigation_state is InvestigationState.SOURCE_UNAVAILABLE
    assert inv.completeness_state is CompletenessState.MATERIAL_SOURCE_UNAVAILABLE


def test_partial_contact_single_candidate(db: Session) -> None:
    inv = _create(db, "Vantar - Castellan", "JR")
    assert len(inv.candidates) == 1
    assert inv.candidates[0].label_fragment == "JR"


def test_multiple_contacts_multiple_candidates(db: Session) -> None:
    inv = _create(db, "Vantar - Castellan", "NOVEXA - Amara - via Delta Trading")
    fragments = sorted(c.label_fragment for c in inv.candidates)
    assert len(fragments) >= 2
    assert "Amara" in fragments


def test_raw_labels_are_immutable(db: Session) -> None:
    inv = _create(db, "Vantar - Castellan", "Jordan Rivera")
    db.commit()
    inv.company_label = "Something Else"
    with pytest.raises(DBAPIError):
        db.flush()
    db.rollback()


def test_investigation_creation_is_audited(db: Session) -> None:
    inv = _create(db, "Vantar - Castellan", "Jordan Rivera")
    actions = db.scalars(
        select(AuditEvent.action).where(AuditEvent.investigation_id == inv.investigation_id)
    ).all()
    assert AuditAction.INVESTIGATION_CREATED in actions


def test_person_candidate_is_not_a_confirmed_person(db: Session) -> None:
    inv = _create(db, "Vantar - Castellan", "Amara")
    cand = db.scalar(
        select(PersonCandidate).where(PersonCandidate.investigation_id == inv.investigation_id)
    )
    assert cand is not None
    # A candidate is never auto-promoted to a resolved Person.
    assert cand.person_id is None
