"""Investigation endpoints (the Stage 1 vertical spine)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..auth import Principal, get_current_principal
from ..db import get_db
from ..models.core import Investigation
from ..models.ops import AuditEvent
from ..schemas import (
    AuditEventOut,
    CreateInvestigationRequest,
    InvestigationOut,
)
from ..services.investigations import create_investigation

router = APIRouter(prefix="/investigations", tags=["investigations"])


def _load(db: Session, investigation_id: uuid.UUID) -> Investigation:
    inv = db.scalar(
        select(Investigation)
        .where(Investigation.investigation_id == investigation_id)
        .options(
            selectinload(Investigation.counterparty),
            selectinload(Investigation.candidates),
        )
    )
    if inv is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Investigation not found."
        )
    return inv


@router.post("", response_model=InvestigationOut, status_code=status.HTTP_201_CREATED)
def create(
    body: CreateInvestigationRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> InvestigationOut:
    # Persist + enqueue the discovery job, then return promptly. The standalone
    # worker (arie_sentinel.jobs.worker) processes the queue; the client refetches
    # the investigation to observe RUNNING -> COMPLETED. Request handlers never
    # process the queue.
    inv = create_investigation(
        db,
        company_label=body.company_label,
        contact_label=body.contact_label,
        actor=principal.email,
    )
    db.commit()
    return InvestigationOut.model_validate(_load(db, inv.investigation_id))


@router.get("/{investigation_id}", response_model=InvestigationOut)
def get_one(
    investigation_id: uuid.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> InvestigationOut:
    return InvestigationOut.model_validate(_load(db, investigation_id))


@router.get("/{investigation_id}/audit", response_model=list[AuditEventOut])
def get_audit(
    investigation_id: uuid.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> list[AuditEventOut]:
    _load(db, investigation_id)  # 404 if missing
    events = db.scalars(
        select(AuditEvent)
        .where(AuditEvent.investigation_id == investigation_id)
        .order_by(AuditEvent.created_at.asc())
    ).all()
    return [AuditEventOut.model_validate(e) for e in events]
