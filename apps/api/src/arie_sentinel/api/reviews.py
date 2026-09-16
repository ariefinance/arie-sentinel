"""Audited analyst dispositions for screening results and findings."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit import record_audit
from ..auth import Principal, get_current_principal
from ..db import get_db
from ..models.core import Investigation
from ..models.enums import AuditAction, ReviewStatus, ScreeningState
from ..models.evidence import AnalystDecision, Finding, ScreeningResult
from ..schemas import FindingOut, ReviewRequest, ScreeningResultOut

router = APIRouter(tags=["reviews"])


@router.post("/screening-results/{result_id}/review", response_model=ScreeningResultOut)
def review_screening(
    result_id: uuid.UUID,
    body: ReviewRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> ScreeningResultOut:
    result = db.get(ScreeningResult, result_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Screening result not found.")
    allowed = {"FALSE_POSITIVE", "CONFIRMED_MATCH", "NEEDS_MORE_INFORMATION"}
    if body.disposition not in allowed:
        raise HTTPException(status_code=422, detail=f"Disposition must be one of {sorted(allowed)}")
    result.analyst_disposition = body.disposition
    result.analyst_rationale = body.rationale
    result.state = (
        ScreeningState.CONFIRMED_MATCH
        if body.disposition == "CONFIRMED_MATCH"
        else ScreeningState.NO_MATERIAL_MATCH
        if body.disposition == "FALSE_POSITIVE"
        else ScreeningState.MATCH_REQUIRES_REVIEW
    )
    states = list(
        db.scalars(
            select(ScreeningResult.state).where(
                ScreeningResult.investigation_id == result.investigation_id,
                ScreeningResult.screening_result_id != result.screening_result_id,
            )
        )
    )
    states.append(result.state)
    order = {
        ScreeningState.NO_MATERIAL_MATCH: 0,
        ScreeningState.POTENTIAL_MATCH: 1,
        ScreeningState.MATCH_REQUIRES_REVIEW: 2,
        ScreeningState.CONFIRMED_MATCH: 3,
    }
    investigation = db.get(Investigation, result.investigation_id)
    if investigation is not None:
        investigation.screening_state = max(states, key=order.__getitem__)
    db.add(
        AnalystDecision(
            investigation_id=result.investigation_id,
            target_type="screening",
            target_ref=result.screening_result_id,
            action=body.disposition,
            rationale=body.rationale,
            actor=principal.email,
        )
    )
    record_audit(
        db,
        actor=principal.email,
        action=AuditAction.REVIEW_SCREENING,
        object_type="screening_result",
        investigation_id=result.investigation_id,
        target_ref=str(result.screening_result_id),
        rationale=body.rationale,
        payload={"disposition": body.disposition},
    )
    db.commit()
    db.refresh(result)
    return ScreeningResultOut.model_validate(result)


@router.post("/findings/{finding_id}/review", response_model=FindingOut)
def review_finding(
    finding_id: uuid.UUID,
    body: ReviewRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> FindingOut:
    finding = db.get(Finding, finding_id)
    if finding is None:
        raise HTTPException(status_code=404, detail="Finding not found.")
    mapping = {
        "CONFIRMED": ReviewStatus.CONFIRMED,
        "DISMISSED": ReviewStatus.DISMISSED,
        "INFO_REQUESTED": ReviewStatus.INFO_REQUESTED,
    }
    if body.disposition not in mapping:
        raise HTTPException(status_code=422, detail=f"Disposition must be one of {sorted(mapping)}")
    finding.review_status = mapping[body.disposition]
    db.add(
        AnalystDecision(
            investigation_id=finding.investigation_id,
            target_type="finding",
            target_ref=finding.finding_id,
            action=body.disposition,
            rationale=body.rationale,
            actor=principal.email,
        )
    )
    record_audit(
        db,
        actor=principal.email,
        action=AuditAction.REVIEW_FINDING,
        object_type="finding",
        investigation_id=finding.investigation_id,
        target_ref=str(finding.finding_id),
        rationale=body.rationale,
        payload={"disposition": body.disposition},
    )
    db.commit()
    db.refresh(finding)
    return FindingOut.model_validate(finding)
