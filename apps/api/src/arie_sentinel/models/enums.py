"""Canonical enumerations.

These MUST mirror docs/SCREEN-STATES.md exactly — no synonyms. They are the
single source of truth for state values across the API and database.
"""

from __future__ import annotations

import enum


class IntakeState(str, enum.Enum):
    SUFFICIENT_FOR_DISCOVERY = "SUFFICIENT_FOR_DISCOVERY"
    CLARIFICATION_REQUIRED = "CLARIFICATION_REQUIRED"


class InvestigationState(str, enum.Enum):
    NOT_STARTED = "NOT_STARTED"
    RUNNING = "RUNNING"
    PARTIAL_RESULTS = "PARTIAL_RESULTS"
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class CompanyIdentityStatus(str, enum.Enum):
    CONFIRMED = "CONFIRMED"
    AMBIGUOUS = "AMBIGUOUS"
    NOT_VERIFIED = "NOT_VERIFIED"


class PersonEvidenceStatus(str, enum.Enum):
    IDENTITY_EVIDENCE_FOUND = "IDENTITY_EVIDENCE_FOUND"
    LIMITED_EVIDENCE = "LIMITED_EVIDENCE"
    IDENTITY_AMBIGUOUS = "IDENTITY_AMBIGUOUS"
    NO_RELIABLE_EVIDENCE_LOCATED = "NO_RELIABLE_EVIDENCE_LOCATED"


class RelationshipState(str, enum.Enum):
    VERIFIED = "VERIFIED"
    CORROBORATED = "CORROBORATED"
    SELF_ASSERTED = "SELF_ASSERTED"
    UNVERIFIED = "UNVERIFIED"
    CONTRADICTED = "CONTRADICTED"


class CompletenessState(str, enum.Enum):
    COMPLETE = "COMPLETE"
    COMPLETE_WITH_LIMITATIONS = "COMPLETE_WITH_LIMITATIONS"
    MATERIAL_SOURCE_UNAVAILABLE = "MATERIAL_SOURCE_UNAVAILABLE"


class ScreeningState(str, enum.Enum):
    NO_MATERIAL_MATCH = "NO_MATERIAL_MATCH"
    POTENTIAL_MATCH = "POTENTIAL_MATCH"
    MATCH_REQUIRES_REVIEW = "MATCH_REQUIRES_REVIEW"
    CONFIRMED_MATCH = "CONFIRMED_MATCH"


class FindingType(str, enum.Enum):
    CONTRADICTION = "CONTRADICTION"
    INCONSISTENCY = "INCONSISTENCY"
    UNVERIFIED_CLAIM = "UNVERIFIED_CLAIM"
    ANOMALY = "ANOMALY"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class ReviewStatus(str, enum.Enum):
    OPEN = "OPEN"
    CONFIRMED = "CONFIRMED"
    DISMISSED = "DISMISSED"
    INFO_REQUESTED = "INFO_REQUESTED"


class Severity(str, enum.Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SourceClass(str, enum.Enum):
    CORPORATE_REGISTRY = "corporate_registry"
    SANCTIONS_PEP_SCREENING = "sanctions_pep_screening"
    DOMAIN_REGISTRATION = "domain_registration"
    OFFICIAL_PUBLICATION = "official_publication"
    COUNTERPARTY_ASSERTED = "counterparty_asserted"
    PRESS_MEDIA = "press_media"
    WEB_PUBLIC = "web_public"
    ANALYST_SUPPLIED = "analyst_supplied"


class AssertedBy(str, enum.Enum):
    COUNTERPARTY = "counterparty"
    SOURCE = "source"
    SYSTEM = "system"


class ClaimSubject(str, enum.Enum):
    COMPANY = "company"
    PERSON = "person"
    DOMAIN = "domain"
    RELATIONSHIP = "relationship"


class LinkRelation(str, enum.Enum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    PARTIALLY_SUPPORTS = "partially_supports"
    CONTEXT = "context"


class ExtractionConfidence(str, enum.Enum):
    AUTHORITATIVE = "authoritative"
    REPORTED = "reported"
    INFERRED = "inferred"


class ImportRowOutcome(str, enum.Enum):
    ACCEPTED = "ACCEPTED"
    MALFORMED_REJECTED = "MALFORMED_REJECTED"


class JobStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class AuditAction(str, enum.Enum):
    INVESTIGATION_CREATED = "INVESTIGATION_CREATED"
    REQUEST_CLARIFICATION = "REQUEST_CLARIFICATION"
    CLARIFICATION_SUPPLIED = "CLARIFICATION_SUPPLIED"
    RESOLVE_IDENTITY = "RESOLVE_IDENTITY"
    LINK_COUNTERPARTY = "LINK_COUNTERPARTY"
    CONFIRM_FINDING = "CONFIRM_FINDING"
    DISMISS_FINDING = "DISMISS_FINDING"
    REQUEST_INFORMATION = "REQUEST_INFORMATION"
    ADD_NOTE = "ADD_NOTE"
    FINALISE_REPORT = "FINALISE_REPORT"
    STATE_CHANGE = "STATE_CHANGE"
    IMPORT_BATCH_CREATED = "IMPORT_BATCH_CREATED"


class Role(str, enum.Enum):
    ANALYST = "analyst"
    MANAGER = "manager"
