"""Analyst worklist — a filtered view over canonical states (no dashboard, no scores)."""

from __future__ import annotations

import enum

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import Principal, get_current_principal
from ..db import get_db
from ..models.core import Investigation
from ..models.enums import (
    CompanyIdentityStatus,
    IntakeState,
    InvestigationState,
    ScreeningState,
)
from ..schemas import WorklistItem

router = APIRouter(prefix="/worklist", tags=["worklist"])


class WorklistFilter(str, enum.Enum):
    """Filters DERIVED from canonical states — no new persisted state.

    Declared as an enum so an unknown filter yields an explicit 422, never a
    silent fallback to `all`.
    """

    ALL = "all"
    MINE = "mine"
    NEEDS_ACTION = "needs_action"
    CLARIFICATION_REQUIRED = "clarification_required"
    IDENTITY_AMBIGUOUS = "identity_ambiguous"
    SCREENING_REVIEW = "screening_review"
    COMPLETED = "completed"


def _needs_action(inv: Investigation) -> bool:
    return (
        inv.intake_state is IntakeState.CLARIFICATION_REQUIRED
        or inv.company_identity_status is CompanyIdentityStatus.AMBIGUOUS
        or inv.screening_state is ScreeningState.MATCH_REQUIRES_REVIEW
    )


@router.get("", response_model=list[WorklistItem])
def list_worklist(
    filter: WorklistFilter = WorklistFilter.ALL,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> list[WorklistItem]:
    stmt = select(Investigation).order_by(Investigation.updated_at.desc())
    if filter is WorklistFilter.MINE:
        stmt = stmt.where(Investigation.created_by == principal.email)
    elif filter is WorklistFilter.CLARIFICATION_REQUIRED:
        stmt = stmt.where(Investigation.intake_state == IntakeState.CLARIFICATION_REQUIRED)
    elif filter is WorklistFilter.IDENTITY_AMBIGUOUS:
        stmt = stmt.where(Investigation.company_identity_status == CompanyIdentityStatus.AMBIGUOUS)
    elif filter is WorklistFilter.SCREENING_REVIEW:
        stmt = stmt.where(Investigation.screening_state == ScreeningState.MATCH_REQUIRES_REVIEW)
    elif filter is WorklistFilter.COMPLETED:
        stmt = stmt.where(Investigation.investigation_state == InvestigationState.COMPLETED)

    rows = db.scalars(stmt).all()
    items = [
        WorklistItem(
            investigation_id=inv.investigation_id,
            company_label=inv.company_label,
            contact_label=inv.contact_label,
            intake_state=inv.intake_state,
            investigation_state=inv.investigation_state,
            company_identity_status=inv.company_identity_status,
            screening_state=inv.screening_state,
            needs_action=_needs_action(inv),
            updated_at=inv.updated_at,
        )
        for inv in rows
    ]
    if filter is WorklistFilter.NEEDS_ACTION:
        items = [i for i in items if i.needs_action]
    return items
