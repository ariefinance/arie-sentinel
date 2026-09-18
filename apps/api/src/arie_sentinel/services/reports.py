"""Auditable Phase 1 Counterparty Integrity Report rendering."""

from __future__ import annotations

import uuid

from jinja2 import Environment, PackageLoader, select_autoescape
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..demo_cases import FICTIONAL_TEST_CASE, PUBLIC_VALIDATION_CASE
from ..models.core import Investigation
from ..models.enums import (
    AuditAction,
    CompletenessState,
    EvidenceState,
    FindingType,
    ReviewStatus,
    ScreeningState,
    SourceClass,
)
from ..models.evidence import Finding, ScreeningResult, Source
from ..models.ops import AuditEvent
from .board import build_board
from .graph import build_graph

_CONTRADICTION_TYPES = {
    FindingType.CONTRADICTION,
    FindingType.INCONSISTENCY,
    FindingType.ANOMALY,
    FindingType.UNVERIFIED_CLAIM,
}


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


def report_headline(session: Session, investigation: Investigation) -> dict[str, str]:
    """A transparent, non-scored headline. No risk %, no SAFE/FRAUD verdict.

    Corroboration is defined explicitly:
    - Strong  = identity confirmed, >=3 corroborating checks, no open contradictions;
    - Partial = identity confirmed, no open contradictions, fewer corroborating checks;
    - Limited = otherwise.
    """
    rows = {row.key: row for row in build_board(session, investigation)}
    findings = session.scalars(
        select(Finding).where(Finding.investigation_id == investigation.investigation_id)
    ).all()
    contradictions = [
        f
        for f in findings
        if f.finding_type in _CONTRADICTION_TYPES and f.review_status is ReviewStatus.OPEN
    ]
    identity_confirmed = rows.get("legal_identity") is not None and rows[
        "legal_identity"
    ].state == (EvidenceState.CONFIRMED.value)
    corroborating_keys = (
        "directors_officers",
        "domain_website",
        "regulatory_footprint",
        "contact_company",
        "lei",
    )
    corroborating = sum(
        1
        for key in corroborating_keys
        if key in rows
        and rows[key].state in {EvidenceState.CONFIRMED.value, EvidenceState.CORROBORATED.value}
    )
    if identity_confirmed and corroborating >= 3 and not contradictions:
        corroboration = "Strong"
    elif identity_confirmed and not contradictions:
        corroboration = "Partial"
    else:
        corroboration = "Limited"
    unavailable = investigation.completeness_state is CompletenessState.MATERIAL_SOURCE_UNAVAILABLE
    actions_row = rows.get("analyst_actions")
    return {
        "identity": "Confirmed" if identity_confirmed else "Not established",
        "corroboration": corroboration,
        "contradictions": (
            f"{len(contradictions)} require review" if contradictions else "None established"
        ),
        "evidence_limitations": "1 or more material sources unavailable"
        if unavailable
        else "None material",
        "analyst_actions": actions_row.detail if actions_row else "None outstanding",
    }


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
    graph = build_graph(session, investigation)
    related_entities = [n for n in graph.nodes if n.id != "company:subject"]
    node_labels = {n.id: n.label for n in graph.nodes}
    # Relationship provenance: FROM / RELATIONSHIP / TO / STATE / BASIS. A claim-only
    # edge carries no source ids; the basis states that explicitly.
    relationships = [
        {
            "from": node_labels.get(edge.source, edge.source),
            "type": edge.type,
            "to": node_labels.get(edge.target, edge.target),
            "state": edge.state,
            "basis": edge.basis,
            "has_sources": bool(edge.source_ids),
        }
        for edge in graph.edges
    ]
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
        headline=report_headline(session, investigation),
        investigation_context=investigation.investigation_context,
        related_entities=related_entities,
        relationships=relationships,
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
