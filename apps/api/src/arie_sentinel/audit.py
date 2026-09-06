"""Audit spine helper. Every state change / human action is appended here."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from .models.enums import AuditAction
from .models.ops import AuditEvent


def record_audit(
    session: Session,
    *,
    actor: str,
    action: AuditAction,
    object_type: str,
    investigation_id: uuid.UUID | None = None,
    target_ref: str | None = None,
    rationale: str | None = None,
    payload: dict[str, Any] | None = None,
) -> AuditEvent:
    """Append an audit event to the current transaction (append-only)."""
    event = AuditEvent(
        investigation_id=investigation_id,
        actor=actor,
        action=action,
        object_type=object_type,
        target_ref=target_ref,
        rationale=rationale,
        payload=payload,
    )
    session.add(event)
    return event
