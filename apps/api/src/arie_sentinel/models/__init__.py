"""ORM models. Importing this package registers all tables on Base.metadata."""

from __future__ import annotations

from .base import Base
from .core import (
    Counterparty,
    EntityCandidate,
    Identifier,
    ImportBatch,
    Investigation,
    Person,
    PersonCandidate,
    Relationship,
)
from .evidence import (
    AnalystDecision,
    Claim,
    ClaimEvidenceLink,
    Evidence,
    Finding,
    ScreeningResult,
    Source,
)
from .ops import AuditEvent, Job

__all__ = [
    "Base",
    "Investigation",
    "Counterparty",
    "EntityCandidate",
    "Person",
    "PersonCandidate",
    "Identifier",
    "Relationship",
    "ImportBatch",
    "Source",
    "Evidence",
    "Claim",
    "ClaimEvidenceLink",
    "Finding",
    "ScreeningResult",
    "AnalystDecision",
    "AuditEvent",
    "Job",
]
