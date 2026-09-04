"""Pydantic v2 API schemas (request/response contracts)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from .models.enums import (
    CompanyIdentityStatus,
    CompletenessState,
    IntakeState,
    InvestigationState,
    PersonEvidenceStatus,
    RelationshipState,
    ScreeningState,
)


class CreateInvestigationRequest(BaseModel):
    company_label: str = Field(min_length=1, max_length=512)
    contact_label: str = Field(min_length=1, max_length=512)


class PersonCandidateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    candidate_id: uuid.UUID
    label_fragment: str
    person_evidence_status: PersonEvidenceStatus | None
    relationship_state: RelationshipState | None
    match_basis: str | None


class CounterpartyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    counterparty_id: uuid.UUID
    legal_name: str
    jurisdiction: str | None
    registry_class: str | None
    registry_id: str | None
    status: str | None
    identity_key: str


class InvestigationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    investigation_id: uuid.UUID
    company_label: str
    contact_label: str
    intake_state: IntakeState
    clarification_reason: str | None
    investigation_state: InvestigationState
    company_identity_status: CompanyIdentityStatus | None
    company_match_basis: str | None
    completeness_state: CompletenessState | None
    screening_state: ScreeningState | None
    counterparty: CounterpartyOut | None = None
    candidates: list[PersonCandidateOut] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class WorklistItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    investigation_id: uuid.UUID
    company_label: str
    contact_label: str
    intake_state: IntakeState
    investigation_state: InvestigationState
    company_identity_status: CompanyIdentityStatus | None
    screening_state: ScreeningState | None
    needs_action: bool
    updated_at: datetime


class AuditEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_id: uuid.UUID
    actor: str
    action: str
    object_type: str
    target_ref: str | None
    rationale: str | None
    created_at: datetime


class HealthOut(BaseModel):
    status: str
    version: str
    database: str
