"""Claims / evidence / findings model — the auditable core.

Truth boundary enforced structurally: Claim.asserted_by + Source.source_class.
AI output is never Evidence unless tied to a stored Source.
Sources are append-only/versioned; evidence references a specific source version.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, uuid_pk
from .core import _enum
from .enums import (
    AssertedBy,
    ClaimSubject,
    ExtractionConfidence,
    FindingType,
    LinkRelation,
    ReviewStatus,
    ScreeningState,
    Severity,
    SourceClass,
)


class Source(Base):
    """Immutable, versioned capture of external material. INSERT-only content."""

    __tablename__ = "source"

    source_id: Mapped[uuid.UUID] = uuid_pk()
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("investigation.investigation_id"), nullable=False
    )
    source_class: Mapped[SourceClass] = mapped_column(_enum(SourceClass), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    origin_ref: Mapped[str | None] = mapped_column(Text)
    retrieved_at: Mapped[datetime] = mapped_column(nullable=False)
    captured_by: Mapped[str] = mapped_column(String(64), nullable=False)  # adapter:<name>|analyst
    content_ref: Mapped[str | None] = mapped_column(Text)
    content_hash: Mapped[str | None] = mapped_column(String(64))
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    supersedes_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("source.source_id"))
    limitations: Mapped[str | None] = mapped_column(Text)
    license_class: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Evidence(Base):
    """A dated observation extracted from exactly one source version."""

    __tablename__ = "evidence"

    evidence_id: Mapped[uuid.UUID] = uuid_pk()
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("source.source_id"), nullable=False)
    observed_value: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    excerpt: Mapped[str | None] = mapped_column(Text)
    extracted_by: Mapped[str] = mapped_column(String(64), nullable=False)  # adapter|model|analyst
    extraction_confidence: Mapped[ExtractionConfidence] = mapped_column(
        _enum(ExtractionConfidence), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Claim(Base):
    """A discrete assertion, attributed to who/what made it (truth boundary)."""

    __tablename__ = "claim"

    claim_id: Mapped[uuid.UUID] = uuid_pk()
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("investigation.investigation_id"), nullable=False
    )
    subject_ref: Mapped[uuid.UUID | None] = mapped_column()  # counterparty/candidate/person id
    claim_type: Mapped[str] = mapped_column(String(64), nullable=False)
    subject: Mapped[ClaimSubject] = mapped_column(_enum(ClaimSubject), nullable=False)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    value: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    asserted_by: Mapped[AssertedBy] = mapped_column(_enum(AssertedBy), nullable=False)
    assertion_origin_ref: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ClaimEvidenceLink(Base):
    __tablename__ = "claim_evidence_link"

    link_id: Mapped[uuid.UUID] = uuid_pk()
    claim_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("claim.claim_id"), nullable=False)
    evidence_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evidence.evidence_id"), nullable=False
    )
    relation: Mapped[LinkRelation] = mapped_column(_enum(LinkRelation), nullable=False)
    created_by: Mapped[str] = mapped_column(String(32), nullable=False, default="system")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Finding(Base, TimestampMixin):
    """A finding in the fixed CLAIM / EVIDENCE / ASSESSMENT / ACTION structure."""

    __tablename__ = "finding"

    finding_id: Mapped[uuid.UUID] = uuid_pk()
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("investigation.investigation_id"), nullable=False
    )
    finding_type: Mapped[FindingType] = mapped_column(_enum(FindingType), nullable=False)
    severity: Mapped[Severity] = mapped_column(_enum(Severity), nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    claim_text: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_text: Mapped[str] = mapped_column(Text, nullable=False)
    assessment_text: Mapped[str] = mapped_column(Text, nullable=False)
    action_text: Mapped[str] = mapped_column(Text, nullable=False)
    related_claim_ids: Mapped[list[uuid.UUID] | None] = mapped_column(ARRAY(PGUUID(as_uuid=True)))
    related_evidence_ids: Mapped[list[uuid.UUID] | None] = mapped_column(
        ARRAY(PGUUID(as_uuid=True))
    )
    review_status: Mapped[ReviewStatus] = mapped_column(
        _enum(ReviewStatus), nullable=False, default=ReviewStatus.OPEN
    )
    created_by: Mapped[str] = mapped_column(String(32), nullable=False, default="system")


class ScreeningResult(Base, TimestampMixin):
    """A screening match/result routed for human adjudication (never auto-decided)."""

    __tablename__ = "screening_result"

    screening_result_id: Mapped[uuid.UUID] = uuid_pk()
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("investigation.investigation_id"), nullable=False
    )
    subject_label: Mapped[str] = mapped_column(String(320), nullable=False)
    list_or_source: Mapped[str] = mapped_column(String(128), nullable=False)
    state: Mapped[ScreeningState] = mapped_column(_enum(ScreeningState), nullable=False)
    match_basis: Mapped[str | None] = mapped_column(Text)
    # Provider-supplied event grouping id (adverse media). Null when not grouped.
    provider_event_group: Mapped[str | None] = mapped_column(String(128))
    article_count: Mapped[int | None] = mapped_column()
    source_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("source.source_id"))


class AnalystDecision(Base):
    """An audited analyst action on a finding/screening result (confirm/dismiss/etc.)."""

    __tablename__ = "analyst_decision"

    decision_id: Mapped[uuid.UUID] = uuid_pk()
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("investigation.investigation_id"), nullable=False
    )
    target_type: Mapped[str] = mapped_column(String(32), nullable=False)  # finding|screening|note
    target_ref: Mapped[uuid.UUID | None] = mapped_column()
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    rationale: Mapped[str | None] = mapped_column(Text)
    actor: Mapped[str] = mapped_column(String(320), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
