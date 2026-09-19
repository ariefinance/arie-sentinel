"""Investigation endpoints (the Stage 1 vertical spine)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..audit import record_audit
from ..auth import Principal, get_current_principal, require_manager
from ..db import get_db
from ..demo_cases import PUBLIC_VALIDATION_CASE
from ..models.core import EntityCandidate, Investigation
from ..models.enums import AuditAction, CompanyIdentityStatus, SourceClass
from ..models.evidence import Finding, ScreeningResult, Source
from ..models.ops import AuditEvent
from ..schemas import (
    AuditEventOut,
    BoardRowOut,
    CreateInvestigationRequest,
    FinaliseReportRequest,
    FindingOut,
    GraphEdgeOut,
    GraphNodeOut,
    InvestigationBoardOut,
    InvestigationOut,
    RelationshipGraphOut,
    ResolveEntityRequest,
    ScreeningResultOut,
    SourceOut,
)
from ..services.board import build_board
from ..services.graph import build_graph
from ..services.investigations import create_investigation, resolve_entity
from ..services.reports import render_report, report_filename

router = APIRouter(prefix="/investigations", tags=["investigations"])


def _load(db: Session, investigation_id: uuid.UUID) -> Investigation:
    inv = db.scalar(
        select(Investigation)
        .where(Investigation.investigation_id == investigation_id)
        .options(
            selectinload(Investigation.counterparty),
            selectinload(Investigation.candidates),
            selectinload(Investigation.entity_candidates),
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
    # the investigation to observe discovery state changes. Request handlers never
    # process the queue.
    inv = create_investigation(
        db,
        company_label=body.company_label,
        contact_label=body.contact_label,
        actor=principal.email,
        investigation_context=body.investigation_context,
        claims=body.claims,
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


@router.get("/{investigation_id}/sources", response_model=list[SourceOut])
def get_sources(
    investigation_id: uuid.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> list[SourceOut]:
    investigation = _load(db, investigation_id)
    rows = db.scalars(
        select(Source)
        .where(Source.investigation_id == investigation_id)
        .order_by(Source.retrieved_at.desc())
    ).all()
    if investigation.case_type == PUBLIC_VALIDATION_CASE and investigation.screening_state is None:
        rows = [row for row in rows if row.source_class is not SourceClass.SANCTIONS_PEP_SCREENING]
    return [SourceOut.model_validate(row) for row in rows]


@router.get("/{investigation_id}/screening", response_model=list[ScreeningResultOut])
def get_screening(
    investigation_id: uuid.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> list[ScreeningResultOut]:
    investigation = _load(db, investigation_id)
    if investigation.case_type == PUBLIC_VALIDATION_CASE and investigation.screening_state is None:
        return []
    rows = db.scalars(
        select(ScreeningResult)
        .where(ScreeningResult.investigation_id == investigation_id)
        .order_by(ScreeningResult.created_at.asc())
    ).all()
    return [ScreeningResultOut.model_validate(row) for row in rows]


@router.get("/{investigation_id}/findings", response_model=list[FindingOut])
def get_findings(
    investigation_id: uuid.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> list[FindingOut]:
    _load(db, investigation_id)
    rows = db.scalars(
        select(Finding)
        .where(Finding.investigation_id == investigation_id)
        .order_by(Finding.created_at.asc())
    ).all()
    return [FindingOut.model_validate(row) for row in rows]


@router.get("/{investigation_id}/board", response_model=InvestigationBoardOut)
def get_board(
    investigation_id: uuid.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> InvestigationBoardOut:
    inv = _load(db, investigation_id)
    rows = build_board(db, inv)
    return InvestigationBoardOut(
        investigation_id=inv.investigation_id,
        investigation_context=inv.investigation_context,
        rows=[
            BoardRowOut(
                key=row.key,
                label=row.label,
                state=row.state,
                detail=row.detail,
                action_required=row.action_required,
                source_ids=row.source_ids,
            )
            for row in rows
        ],
    )


@router.get("/{investigation_id}/graph", response_model=RelationshipGraphOut)
def get_graph(
    investigation_id: uuid.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> RelationshipGraphOut:
    inv = _load(db, investigation_id)
    graph = build_graph(db, inv)
    return RelationshipGraphOut(
        investigation_id=inv.investigation_id,
        nodes=[
            GraphNodeOut(id=n.id, type=n.type, label=n.label, detail=n.detail) for n in graph.nodes
        ],
        edges=[
            GraphEdgeOut(
                source=e.source,
                target=e.target,
                type=e.type,
                basis=e.basis,
                state=e.state,
                source_ids=e.source_ids,
            )
            for e in graph.edges
        ],
    )


@router.get("/{investigation_id}/company", response_model=InvestigationOut)
def get_company(
    investigation_id: uuid.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> InvestigationOut:
    return InvestigationOut.model_validate(_load(db, investigation_id))


@router.get("/{investigation_id}/person", response_model=InvestigationOut)
def get_person(
    investigation_id: uuid.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> InvestigationOut:
    return InvestigationOut.model_validate(_load(db, investigation_id))


@router.post("/{investigation_id}/resolve-entity", response_model=InvestigationOut)
def resolve(
    investigation_id: uuid.UUID,
    body: ResolveEntityRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> InvestigationOut:
    inv = _load(db, investigation_id)
    if inv.company_identity_status is not None and inv.company_identity_status.value == "CONFIRMED":
        raise HTTPException(status_code=409, detail="Entity is already resolved.")
    candidate = db.get(EntityCandidate, body.candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found.")
    try:
        resolve_entity(db, inv, candidate, actor=principal.email, rationale=body.rationale)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    db.commit()
    return InvestigationOut.model_validate(_load(db, investigation_id))


@router.post("/{investigation_id}/report")
def report(
    investigation_id: uuid.UUID,
    body: FinaliseReportRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_manager),
) -> Response:
    inv = _load(db, investigation_id)
    if inv.company_identity_status is not CompanyIdentityStatus.CONFIRMED:
        raise HTTPException(status_code=409, detail="Resolve the legal entity before reporting.")
    try:
        pdf = render_report(db, inv)
    except (ImportError, OSError, RuntimeError) as exc:
        raise HTTPException(status_code=503, detail="PDF renderer is unavailable.") from exc
    record_audit(
        db,
        actor=principal.email,
        action=AuditAction.FINALISE_REPORT,
        object_type="report",
        investigation_id=inv.investigation_id,
        payload={"format": "pdf", "confirm_finalise": body.confirm_finalise},
    )
    db.commit()
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{report_filename(investigation_id)}"'
        },
    )
