"""Auditable Phase 1 Counterparty Integrity Report rendering."""

from __future__ import annotations

import uuid

from jinja2 import Environment, PackageLoader, select_autoescape
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.core import Investigation
from ..models.evidence import Finding, ScreeningResult, Source
from ..models.ops import AuditEvent


def render_report(session: Session, investigation: Investigation) -> bytes:
    # Lazy import keeps the API usable on developer machines without the native
    # Pango runtime; production/CI install the documented WeasyPrint libraries.
    from weasyprint import HTML

    sources = session.scalars(
        select(Source)
        .where(Source.investigation_id == investigation.investigation_id)
        .order_by(Source.retrieved_at.asc())
    ).all()
    findings = session.scalars(
        select(Finding).where(Finding.investigation_id == investigation.investigation_id)
    ).all()
    screening = session.scalars(
        select(ScreeningResult).where(
            ScreeningResult.investigation_id == investigation.investigation_id
        )
    ).all()
    audit = session.scalars(
        select(AuditEvent).where(AuditEvent.investigation_id == investigation.investigation_id)
    ).all()
    env = Environment(
        loader=PackageLoader("arie_sentinel", "templates"),
        autoescape=select_autoescape(["html"]),
    )
    html = env.get_template("report.html").render(
        investigation=investigation,
        sources=sources,
        findings=findings,
        screening=screening,
        audit=audit,
    )
    result = HTML(string=html).write_pdf()
    if not isinstance(result, bytes):
        raise RuntimeError("Report renderer did not return PDF bytes")
    return result


def report_filename(investigation_id: uuid.UUID) -> str:
    return f"sentinel-{investigation_id}.pdf"
