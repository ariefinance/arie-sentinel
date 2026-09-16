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
    ReviewStatus,
    ScreeningState,
    SourceClass,
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


class EntityCandidateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    entity_candidate_id: uuid.UUID
    legal_name: str
    jurisdiction: str | None
    registry_class: str | None
    registry_id: str | None
    legal_status: str | None
    registered_address: str | None
    incorporation_date: str | None
    lei: str | None
    alternative_names: list[str] | None
    provider: str
    source_ref: str | None
    retrieved_at: datetime
    match_basis: str | None


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
    entity_candidates: list[EntityCandidateOut] = Field(default_factory=list)
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


class ResolveEntityRequest(BaseModel):
    candidate_id: uuid.UUID
    rationale: str = Field(min_length=3, max_length=2000)


class ReviewRequest(BaseModel):
    disposition: str = Field(min_length=3, max_length=32)
    rationale: str = Field(min_length=3, max_length=2000)


class SourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source_id: uuid.UUID
    source_class: SourceClass
    title: str
    origin_ref: str | None
    retrieved_at: datetime
    captured_by: str
    limitations: str | None
    license_class: str | None


class ScreeningResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    screening_result_id: uuid.UUID
    subject_label: str
    list_or_source: str
    state: ScreeningState
    match_basis: str | None
    matched_profile_id: str | None
    match_score: float | None
    match_explanation: dict[str, object] | None
    matched_identifiers: dict[str, object] | None
    datasets: list[str] | None
    source_id: uuid.UUID | None
    analyst_disposition: str | None
    analyst_rationale: str | None
    created_at: datetime


class FindingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    finding_id: uuid.UUID
    finding_type: str
    severity: str
    title: str
    claim_text: str
    evidence_text: str
    assessment_text: str
    action_text: str
    related_evidence_ids: list[uuid.UUID] | None
    review_status: ReviewStatus
    created_at: datetime
