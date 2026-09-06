"""Bulk list import (XLSX/CSV).

Idempotency model (frozen record/entity semantics):
- An Investigation is a *management record*. The same company/contact may
  legitimately recur across orders, products, source lists, and dates, so rows
  are NEVER globally deduplicated by their labels.
- A row is identified by (import_batch, source row index). Two rows with
  identical labels in one file each create their own Investigation.
- Exact same FILE re-import is deduplicated by ImportBatch.file_fingerprint:
  it does not create a second batch/investigation set; the prior result is
  returned deterministically.
- Counterparty deduplication happens later, at the resolved identity_key — not
  at management-record intake.
No ETL framework; no import wizard.
"""

from __future__ import annotations

import csv
import hashlib
import io
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit import record_audit
from ..models.core import ImportBatch, Investigation
from ..models.enums import AuditAction, ImportRowOutcome
from .investigations import create_investigation

# Columns retained as non-evidentiary case_context (never evidence).
CONTEXT_COLUMNS: frozenset[str] = frozenset(
    {
        "buyer_seller",
        "management_reference",
        "internal_tier",
        "product",
        "quantity",
        "incoterm",
        "port",
        "commercial_comments",
    }
)


def file_fingerprint(data: bytes) -> str:
    """Deterministic SHA-256 of the uploaded file (exact-file dedup)."""
    return hashlib.sha256(data).hexdigest()


@dataclass
class ParsedRow:
    index: int
    values: dict[str, str]


@dataclass
class RowResult:
    index: int
    outcome: ImportRowOutcome
    reason: str | None = None
    investigation_id: str | None = None
    company_label: str | None = None


@dataclass
class ImportResult:
    import_batch_id: str
    duplicate_file: bool
    total_rows: int
    accepted: int
    rejected: int
    linked_existing: int
    rows: list[RowResult] = field(default_factory=list)


def parse_csv(data: bytes) -> list[ParsedRow]:
    text = data.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    rows: list[ParsedRow] = []
    for i, raw in enumerate(reader):
        values = {(k or "").strip().lower(): (v or "").strip() for k, v in raw.items()}
        rows.append(ParsedRow(index=i, values=values))
    return rows


def parse_xlsx(data: bytes) -> list[ParsedRow]:
    from openpyxl import load_workbook

    wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    ws = wb.active
    rows: list[ParsedRow] = []
    header: list[str] = []
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        cells = ["" if c is None else str(c).strip() for c in row]
        if i == 0:
            header = [c.lower() for c in cells]
            continue
        if not any(cells):
            continue
        values = {header[j]: cells[j] for j in range(min(len(header), len(cells)))}
        rows.append(ParsedRow(index=i - 1, values=values))
    wb.close()
    return rows


def parse_file(filename: str, data: bytes) -> tuple[list[ParsedRow], str]:
    lower = filename.lower()
    if lower.endswith(".csv"):
        return parse_csv(data), "csv"
    if lower.endswith(".xlsx"):
        return parse_xlsx(data), "xlsx"
    raise ValueError("Unsupported file type: expected .csv or .xlsx")


def _extract_context(values: dict[str, str]) -> dict[str, Any] | None:
    ctx = {k: v for k, v in values.items() if k in CONTEXT_COLUMNS and v}
    return ctx or None


def _existing_batch_result(session: Session, batch: ImportBatch) -> ImportResult:
    """Deterministically report a previously-imported file's investigations."""
    invs = session.scalars(
        select(Investigation)
        .where(Investigation.import_batch_id == batch.import_batch_id)
        .order_by(Investigation.source_row_ref)
    ).all()
    result = ImportResult(
        import_batch_id=str(batch.import_batch_id),
        duplicate_file=True,
        total_rows=batch.row_count,
        accepted=0,
        rejected=0,
        linked_existing=len(invs),
    )
    for inv in invs:
        result.rows.append(
            RowResult(
                index=int(inv.source_row_ref) if inv.source_row_ref is not None else -1,
                outcome=ImportRowOutcome.ACCEPTED,
                reason="Linked to the existing import of this file (idempotent).",
                investigation_id=str(inv.investigation_id),
                company_label=inv.company_label,
            )
        )
    return result


def import_rows(
    session: Session,
    *,
    filename: str,
    data: bytes,
    actor: str,
    company_column: str = "company_label",
    contact_column: str = "contact_label",
) -> ImportResult:
    """One Investigation per valid row; malformed rows isolated; exact-file re-import idempotent."""
    fingerprint = file_fingerprint(data)

    # Exact same file already imported -> return the prior result, create nothing.
    existing = session.scalar(
        select(ImportBatch).where(ImportBatch.file_fingerprint == fingerprint).limit(1)
    )
    if existing is not None:
        return _existing_batch_result(session, existing)

    parsed, fmt = parse_file(filename, data)

    batch = ImportBatch(
        filename=filename,
        source_format=fmt,
        file_fingerprint=fingerprint,
        imported_by=actor,
        row_count=len(parsed),
    )
    session.add(batch)
    session.flush()
    record_audit(
        session,
        actor=actor,
        action=AuditAction.IMPORT_BATCH_CREATED,
        object_type="import_batch",
        target_ref=str(batch.import_batch_id),
        payload={"filename": filename, "row_count": len(parsed)},
    )

    result = ImportResult(
        import_batch_id=str(batch.import_batch_id),
        duplicate_file=False,
        total_rows=len(parsed),
        accepted=0,
        rejected=0,
        linked_existing=0,
    )

    for prow in parsed:
        company = prow.values.get(company_column, "").strip()
        contact = prow.values.get(contact_column, "").strip()
        if not company or not contact:
            result.rows.append(
                RowResult(
                    index=prow.index,
                    outcome=ImportRowOutcome.MALFORMED_REJECTED,
                    reason="Missing required company_label or contact_label.",
                )
            )
            result.rejected += 1
            continue

        try:
            # SAVEPOINT per row: a bad row rolls back only itself (isolation).
            with session.begin_nested():
                inv = create_investigation(
                    session,
                    company_label=company,
                    contact_label=contact,
                    actor=actor,
                    case_context=_extract_context(prow.values),
                    import_batch_id=batch.import_batch_id,
                    source_row_ref=str(prow.index),
                )
                session.flush()
            result.rows.append(
                RowResult(
                    index=prow.index,
                    outcome=ImportRowOutcome.ACCEPTED,
                    investigation_id=str(inv.investigation_id),
                    company_label=company,
                )
            )
            result.accepted += 1
        except Exception as exc:  # noqa: BLE001 - one bad row must not corrupt others
            result.rows.append(
                RowResult(
                    index=prow.index,
                    outcome=ImportRowOutcome.MALFORMED_REJECTED,
                    reason=f"{type(exc).__name__}: {exc}",
                )
            )
            result.rejected += 1

    return result
