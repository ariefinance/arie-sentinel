"""Operational models: append-only audit log and the PostgreSQL-backed job queue."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, uuid_pk
from .core import _enum
from .enums import AuditAction, JobStatus


class AuditEvent(Base):
    """Append-only audit record. Never updated or deleted."""

    __tablename__ = "audit_event"

    event_id: Mapped[uuid.UUID] = uuid_pk()
    investigation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("investigation.investigation_id")
    )
    actor: Mapped[str] = mapped_column(String(320), nullable=False)
    action: Mapped[AuditAction] = mapped_column(_enum(AuditAction, length=48), nullable=False)
    object_type: Mapped[str] = mapped_column(String(48), nullable=False)
    target_ref: Mapped[str | None] = mapped_column(String(64))
    rationale: Mapped[str | None] = mapped_column(Text)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Job(Base, TimestampMixin):
    """A unit of asynchronous work, claimed via SELECT ... FOR UPDATE SKIP LOCKED."""

    __tablename__ = "job"

    job_id: Mapped[uuid.UUID] = uuid_pk()
    investigation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("investigation.investigation_id")
    )
    job_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[JobStatus] = mapped_column(
        _enum(JobStatus), nullable=False, default=JobStatus.PENDING, index=True
    )
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    attempts: Mapped[int] = mapped_column(nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(nullable=False, default=3)
    last_error: Mapped[str | None] = mapped_column(Text)
    run_after: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    locked_by: Mapped[str | None] = mapped_column(String(128))
