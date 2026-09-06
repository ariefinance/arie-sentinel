"""Core domain models: the record/entity spine.

Frozen distinctions (docs/CLAIMS-EVIDENCE-MODEL.md):
- Investigation (management record) != Counterparty (resolved legal entity).
- Raw labels != resolved identities (labels are immutable).
- PersonCandidate != confirmed Person.
- case_context != evidence.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, uuid_pk
from .enums import (
    CompanyIdentityStatus,
    CompletenessState,
    IntakeState,
    InvestigationState,
    PersonEvidenceStatus,
    RelationshipState,
    ScreeningState,
)


def _enum(col_enum: type, length: int = 40) -> SAEnum:
    # native_enum=False -> VARCHAR + CHECK constraint: structural enforcement,
    # migration-friendly (no Postgres ENUM type churn).
    return SAEnum(col_enum, native_enum=False, length=length, validate_strings=True)


def text_not_null(column: str) -> Any:
    """Helper for a partial-index predicate '<column> IS NOT NULL'."""
    from sqlalchemy import text

    return text(f"{column} IS NOT NULL")


class ImportBatch(Base, TimestampMixin):
    __tablename__ = "import_batch"

    import_batch_id: Mapped[uuid.UUID] = uuid_pk()
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    source_format: Mapped[str] = mapped_column(String(8), nullable=False)  # xlsx | csv
    # Deterministic fingerprint of the uploaded file (duplicate-file detection).
    file_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    imported_by: Mapped[str] = mapped_column(String(320), nullable=False)
    row_count: Mapped[int] = mapped_column(nullable=False, default=0)

    investigations: Mapped[list[Investigation]] = relationship(back_populates="import_batch")


class Counterparty(Base, TimestampMixin):
    """Resolved legal entity — shared and deduplicated across investigations."""

    __tablename__ = "counterparty"

    counterparty_id: Mapped[uuid.UUID] = uuid_pk()
    legal_name: Mapped[str] = mapped_column(String(512), nullable=False)
    registry_class: Mapped[str | None] = mapped_column(String(64))
    registry_id: Mapped[str | None] = mapped_column(String(128))
    jurisdiction: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str | None] = mapped_column(String(64))
    # Canonical dedupe key = f(jurisdiction, registry_id). UNIQUE: a repeated
    # organisation links here rather than creating a duplicate. Never label-based.
    identity_key: Mapped[str] = mapped_column(String(256), nullable=False, unique=True)
    first_resolved_at: Mapped[datetime | None] = mapped_column()

    investigations: Mapped[list[Investigation]] = relationship(back_populates="counterparty")
    identifiers: Mapped[list[Identifier]] = relationship(back_populates="counterparty")


class Person(Base, TimestampMixin):
    """Resolved individual — shareable across investigations."""

    __tablename__ = "person"

    person_id: Mapped[uuid.UUID] = uuid_pk()
    display_name: Mapped[str] = mapped_column(String(320), nullable=False)
    identity_key: Mapped[str | None] = mapped_column(String(256))
    first_resolved_at: Mapped[datetime | None] = mapped_column()

    __table_args__ = (
        # Unique only where an authoritative key exists (partial unique index).
        Index(
            "uq_person_identity_key",
            "identity_key",
            unique=True,
            postgresql_where=text_not_null("identity_key"),
        ),
    )


class Investigation(Base, TimestampMixin):
    """One management record. Owns the raw labels; references a shared Counterparty."""

    __tablename__ = "investigation"

    investigation_id: Mapped[uuid.UUID] = uuid_pk()

    # Raw management labels — IMMUTABLE (enforced by DB trigger; see migration).
    company_label: Mapped[str] = mapped_column(String(512), nullable=False)
    contact_label: Mapped[str] = mapped_column(String(512), nullable=False)

    intake_state: Mapped[IntakeState] = mapped_column(_enum(IntakeState), nullable=False)
    clarification_reason: Mapped[str | None] = mapped_column(Text)

    investigation_state: Mapped[InvestigationState] = mapped_column(
        _enum(InvestigationState), nullable=False, default=InvestigationState.NOT_STARTED
    )
    # Meaningful only once intake_state = SUFFICIENT_FOR_DISCOVERY.
    company_identity_status: Mapped[CompanyIdentityStatus | None] = mapped_column(
        _enum(CompanyIdentityStatus)
    )
    company_match_basis: Mapped[str | None] = mapped_column(Text)

    counterparty_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("counterparty.counterparty_id")
    )
    completeness_state: Mapped[CompletenessState | None] = mapped_column(_enum(CompletenessState))
    screening_state: Mapped[ScreeningState | None] = mapped_column(_enum(ScreeningState))

    # Non-evidentiary imported commercial/management context. Never evidence.
    case_context: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    # Bulk-import provenance (all null for single investigations).
    # A management record is identified by (batch, source row), NOT by its labels:
    # the same company/contact may legitimately recur across rows/files/orders.
    import_batch_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("import_batch.import_batch_id")
    )
    source_row_ref: Mapped[str | None] = mapped_column(String(64))

    created_by: Mapped[str] = mapped_column(String(320), nullable=False)

    counterparty: Mapped[Counterparty | None] = relationship(back_populates="investigations")
    import_batch: Mapped[ImportBatch | None] = relationship(back_populates="investigations")
    candidates: Mapped[list[PersonCandidate]] = relationship(
        back_populates="investigation", cascade="all, delete-orphan"
    )

    __table_args__ = (
        # A row is identified by (batch, source row index) — NOT by label content.
        # This makes re-processing a batch idempotent while allowing two rows with
        # identical labels in one file to each create their own Investigation.
        UniqueConstraint("import_batch_id", "source_row_ref", name="uq_import_batch_row"),
    )


class PersonCandidate(Base, TimestampMixin):
    """0..N candidates derived from one raw contact_label. Never a confirmed Person by itself."""

    __tablename__ = "person_candidate"

    candidate_id: Mapped[uuid.UUID] = uuid_pk()
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("investigation.investigation_id"), nullable=False
    )
    label_fragment: Mapped[str] = mapped_column(String(512), nullable=False)
    person_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("person.person_id"))
    person_evidence_status: Mapped[PersonEvidenceStatus | None] = mapped_column(
        _enum(PersonEvidenceStatus)
    )
    relationship_state: Mapped[RelationshipState | None] = mapped_column(_enum(RelationshipState))
    match_basis: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[str] = mapped_column(String(32), nullable=False, default="system")

    investigation: Mapped[Investigation] = relationship(back_populates="candidates")


class Identifier(Base, TimestampMixin):
    """Structured identifiers attached to a Counterparty or Person (registry no., domain, LEI…)."""

    __tablename__ = "identifier"

    identifier_id: Mapped[uuid.UUID] = uuid_pk()
    counterparty_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("counterparty.counterparty_id")
    )
    person_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("person.person_id"))
    id_type: Mapped[str] = mapped_column(String(64), nullable=False)
    id_value: Mapped[str] = mapped_column(String(256), nullable=False)

    counterparty: Mapped[Counterparty | None] = relationship(back_populates="identifiers")


class Relationship(Base, TimestampMixin):
    """Resolved company<->person or company<->domain relationship with a state and basis."""

    __tablename__ = "relationship"

    relationship_id: Mapped[uuid.UUID] = uuid_pk()
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("investigation.investigation_id"), nullable=False
    )
    counterparty_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("counterparty.counterparty_id")
    )
    person_candidate_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("person_candidate.candidate_id")
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False)  # company_person | company_domain
    state: Mapped[RelationshipState] = mapped_column(_enum(RelationshipState), nullable=False)
    basis: Mapped[str | None] = mapped_column(Text)
