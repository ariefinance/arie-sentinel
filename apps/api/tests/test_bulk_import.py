"""Bulk import semantics: record-per-row, file-level idempotency, Counterparty dedup."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from arie_sentinel.models.core import Counterparty, Investigation
from arie_sentinel.models.enums import ImportRowOutcome
from arie_sentinel.services.bulk_import import file_fingerprint, import_rows
from arie_sentinel.services.investigations import run_discovery

ANALYST = "analyst@example.test"

# Row 3 intentionally repeats row 0's labels; row 1 is malformed (no company).
CSV_A = (
    b"company_label,contact_label,internal_tier,product\n"
    b"Vantar - Castellan,Jordan Rivera,T2,Product-A\n"
    b",Amara,T1,Product-A\n"
    b"Castellan Trading,Amara,T2,Product-A\n"
    b"Vantar - Castellan,Jordan Rivera,T2,Product-A\n"
)
# Same company/contact as CSV_A row 0, but a different file (different product).
CSV_B = b"company_label,contact_label,product\nVantar - Castellan,Jordan Rivera,Product-B\n"


def _count(db: Session, model) -> int:
    return db.scalar(select(func.count()).select_from(model))


def test_fingerprint_deterministic() -> None:
    assert file_fingerprint(CSV_A) == file_fingerprint(CSV_A)
    assert file_fingerprint(CSV_A) != file_fingerprint(CSV_B)


def test_row_per_record_and_malformed_isolation(db: Session) -> None:
    result = import_rows(db, filename="a.csv", data=CSV_A, actor=ANALYST)
    db.flush()
    # CSV has 4 data rows; row index 1 has an empty company -> malformed.
    assert result.total_rows == 4
    assert result.accepted == 3
    assert result.rejected == 1
    assert {r.index: r.outcome for r in result.rows}[1] is ImportRowOutcome.MALFORMED_REJECTED
    assert _count(db, Investigation) == 3


def test_identical_rows_are_not_collapsed(db: Session) -> None:
    import_rows(db, filename="a.csv", data=CSV_A, actor=ANALYST)
    db.flush()
    # Rows 0 and 3 share labels but are distinct management records.
    same = db.scalars(
        select(Investigation).where(Investigation.company_label == "Vantar - Castellan")
    ).all()
    assert len(same) == 2
    assert {i.source_row_ref for i in same} == {"0", "3"}


def test_exact_same_file_reimport_is_idempotent(db: Session) -> None:
    import_rows(db, filename="a.csv", data=CSV_A, actor=ANALYST)
    db.flush()
    before = _count(db, Investigation)
    result = import_rows(db, filename="a.csv", data=CSV_A, actor=ANALYST)
    db.flush()
    after = _count(db, Investigation)
    assert before == after == 3
    assert result.duplicate_file is True
    assert result.accepted == 0
    assert result.linked_existing == 3


def test_different_file_same_labels_creates_new_investigation(db: Session) -> None:
    import_rows(db, filename="a.csv", data=CSV_A, actor=ANALYST)
    db.flush()
    before = _count(db, Investigation)
    import_rows(db, filename="b.csv", data=CSV_B, actor=ANALYST)
    db.flush()
    after = _count(db, Investigation)
    # A new, different file with the same company/contact is a new management record.
    assert after == before + 1


def test_repeated_counterparty_dedups_at_identity_key(db: Session) -> None:
    import_rows(db, filename="a.csv", data=CSV_A, actor=ANALYST)
    db.flush()
    # Resolve every sufficient investigation.
    for inv in db.scalars(select(Investigation)).all():
        run_discovery(db, inv.investigation_id)
    db.flush()
    # Three investigations (2x "Vantar - Castellan", 1x "Castellan Trading") but the
    # two Vantar rows share one Counterparty; Castellan is another -> 2 counterparties.
    assert _count(db, Counterparty) == 2
    vantar = db.scalars(
        select(Investigation).where(Investigation.company_label == "Vantar - Castellan")
    ).all()
    assert vantar[0].counterparty_id is not None
    assert vantar[0].counterparty_id == vantar[1].counterparty_id


def test_commercial_columns_go_to_case_context(db: Session) -> None:
    import_rows(db, filename="a.csv", data=CSV_A, actor=ANALYST)
    db.flush()
    inv = db.scalar(select(Investigation).where(Investigation.company_label == "Castellan Trading"))
    assert inv is not None and inv.case_context is not None
    assert inv.case_context.get("internal_tier") == "T2"
    assert inv.case_context.get("product") == "Product-A"
