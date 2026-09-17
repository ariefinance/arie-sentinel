"""Auditable Phase 1 Counterparty Integrity Report rendering."""

from __future__ import annotations

import uuid

from jinja2 import Environment, PackageLoader, select_autoescape
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..demo_cases import FICTIONAL_TEST_CASE, PUBLIC_VALIDATION_CASE
from ..models.core import Investigation
from ..models.enums import AuditAction, CompletenessState, ScreeningState, SourceClass
from ..models.evidence import Finding, ScreeningResult, Source
from ..models.ops import AuditEvent


def screening_summary(investigation: Investigation, screening: list[ScreeningResult]) -> str | None:
    if investigation.case_type == PUBLIC_VALIDATION_CASE and investigation.screening_state is None:
        return (
            "Live sanctions/PEP screening was not performed in this management-demo "
            "environment. No screening conclusion should be inferred."
        )
    if screening:
        return None
    if investigation.screening_state is ScreeningState.NO_MATERIAL_MATCH:
        # A clean result on fixture data must never read as a real screening clearance.
        if investigation.case_type == FICTIONAL_TEST_CASE:
            return "Fictional screening scenario completed with no material fixture matches."
        return "Screening completed and returned no material matches."
    if investigation.completeness_state is CompletenessState.MATERIAL_SOURCE_UNAVAILABLE:
        return "Screening was not completed because a required source was unavailable."
    return "Screening has not yet completed."


def case_type_label(investigation: Investigation) -> str:
    if investigation.case_type == PUBLIC_VALIDATION_CASE:
        return "Public Validation Case"
    if investigation.case_type == FICTIONAL_TEST_CASE:
        return "Fictional Test Case"
    return "Live investigation"


def demo_marker(investigation: Investigation) -> dict[str, str] | None:
    """Concise non-live marker for demo reports, so the case context survives export."""
    if investigation.case_type == FICTIONAL_TEST_CASE:
        return {
            "banner": "MANAGEMENT DEMO · FICTIONAL TEST DATA · NON-LIVE",
            "note": (
                "This report demonstrates the Sentinel workflow using fictional fixture data. "
                "It is not a live registry, sanctions, PEP or adverse-media result."
            ),
        }
    if investigation.case_type == PUBLIC_VALIDATION_CASE:
        return {
            "banner": "MANAGEMENT DEMO · PUBLIC VALIDATION · NON-LIVE SCREENING",
            "note": (
                "Live sanctions/PEP screening was not performed. No screening conclusion should "
                "be inferred. Public-source facts carry their own stated limitations below."
            ),
        }
    return None


def _resolution_event(session: Session, investigation: Investigation) -> AuditEvent | None:
    """The analyst RESOLVE_IDENTITY audit event (actor, timestamp, rationale)."""
    return session.scalar(
        select(AuditEvent)
        .where(
            AuditEvent.investigation_id == investigation.investigation_id,
            AuditEvent.action == AuditAction.RESOLVE_IDENTITY,
        )
        .order_by(AuditEvent.created_at.asc())
    )


def build_report_html(session: Session, investigation: Investigation) -> str:
    """Render the report to HTML from stored records (PDF-independent, testable)."""
    sources = session.scalars(
        select(Source)
        .where(Source.investigation_id == investigation.investigation_id)
        .order_by(Source.retrieved_at.asc())
    ).all()
    if investigation.case_type == PUBLIC_VALIDATION_CASE and investigation.screening_state is None:
        sources = [
            source
            for source in sources
            if source.source_class is not SourceClass.SANCTIONS_PEP_SCREENING
        ]
    findings = session.scalars(
        select(Finding).where(Finding.investigation_id == investigation.investigation_id)
    ).all()
    screening = session.scalars(
        select(ScreeningResult).where(
            ScreeningResult.investigation_id == investigation.investigation_id
        )
    ).all()
    if investigation.case_type == PUBLIC_VALIDATION_CASE and investigation.screening_state is None:
        screening = []
    audit = session.scalars(
        select(AuditEvent).where(AuditEvent.investigation_id == investigation.investigation_id)
    ).all()
    env = Environment(
        loader=PackageLoader("arie_sentinel", "templates"),
        autoescape=select_autoescape(["html"]),
    )
    return env.get_template("report.html").render(
        investigation=investigation,
        sources=sources,
        findings=findings,
        screening=screening,
        screening_summary=screening_summary(investigation, list(screening)),
        audit=audit,
        case_type_label=case_type_label(investigation),
        demo_marker=demo_marker(investigation),
        resolution_event=_resolution_event(session, investigation),
    )


def render_report(session: Session, investigation: Investigation) -> bytes:
    # Lazy import keeps the API usable on developer machines without the native
    # Pango runtime; production/CI install the documented WeasyPrint libraries.
    from weasyprint import HTML

    html = build_report_html(session, investigation)
    result = HTML(string=html).write_pdf()
    if not isinstance(result, bytes):
        raise RuntimeError("Report renderer did not return PDF bytes")
    return result


def report_filename(investigation_id: uuid.UUID) -> str:
    return f"sentinel-{investigation_id}.pdf"
