"""Database-level data-integrity guards (triggers) and typed columns."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from arie_sentinel.models.core import Investigation
from arie_sentinel.models.enums import (
    ExtractionConfidence,
    FindingType,
    Severity,
    SourceClass,
)
from arie_sentinel.models.evidence import Evidence, Finding, Source
from arie_sentinel.models.ops import AuditEvent
from arie_sentinel.services.investigations import create_investigation

ANALYST = "analyst@example.test"


def _investigation(db: Session) -> Investigation:
    inv = create_investigation(
        db, company_label="Vantar - Castellan", contact_label="Jordan Rivera", actor=ANALYST
    )
    db.commit()
    return inv


def _source(db: Session, inv: Investigation) -> Source:
    src = Source(
        investigation_id=inv.investigation_id,
        source_class=SourceClass.CORPORATE_REGISTRY,
        title="Registry record",
        retrieved_at=datetime.now(UTC),
        captured_by="adapter:corporate_registry",
    )
    db.add(src)
    db.commit()
    return src


def test_source_is_immutable(db: Session) -> None:
    src = _source(db, _investigation(db))
    with pytest.raises(DBAPIError):
        db.execute(
            text("UPDATE source SET title = 'tampered' WHERE source_id = :i"),
            {"i": str(src.source_id)},
        )
    db.rollback()
    with pytest.raises(DBAPIError):
        db.execute(text("DELETE FROM source WHERE source_id = :i"), {"i": str(src.source_id)})
    db.rollback()


def test_evidence_is_append_only(db: Session) -> None:
    inv = _investigation(db)
    src = _source(db, inv)
    ev = Evidence(
        source_id=src.source_id,
        excerpt="Date of incorporation: 14 February 2025",
        extracted_by="adapter:corporate_registry",
        extraction_confidence=ExtractionConfidence.AUTHORITATIVE,
    )
    db.add(ev)
    db.commit()
    with pytest.raises(DBAPIError):
        db.execute(
            text("UPDATE evidence SET excerpt = 'x' WHERE evidence_id = :i"),
            {"i": str(ev.evidence_id)},
        )
    db.rollback()
    with pytest.raises(DBAPIError):
        db.execute(text("DELETE FROM evidence WHERE evidence_id = :i"), {"i": str(ev.evidence_id)})
    db.rollback()


def test_audit_is_append_only(db: Session) -> None:
    inv = _investigation(db)
    ev = db.scalar(select(AuditEvent).where(AuditEvent.investigation_id == inv.investigation_id))
    assert ev is not None
    with pytest.raises(DBAPIError):
        db.execute(
            text("UPDATE audit_event SET actor = 'x' WHERE event_id = :i"),
            {"i": str(ev.event_id)},
        )
    db.rollback()


def test_finding_related_ids_roundtrip_as_uuid(db: Session) -> None:
    inv = _investigation(db)
    claim_ids = [uuid.uuid4(), uuid.uuid4()]
    finding = Finding(
        investigation_id=inv.investigation_id,
        finding_type=FindingType.INCONSISTENCY,
        severity=Severity.MEDIUM,
        title="Operating history",
        claim_text="Website states operations since 2011.",
        evidence_text="Incorporated 14 February 2025.",
        assessment_text="Stated history predates the current legal entity.",
        action_text="Clarify corporate history.",
        related_claim_ids=claim_ids,
    )
    db.add(finding)
    db.commit()
    db.expire_all()
    reloaded = db.get(Finding, finding.finding_id)
    assert reloaded.related_claim_ids == claim_ids
    assert all(isinstance(x, uuid.UUID) for x in reloaded.related_claim_ids)
