"""Structural data-integrity guards (triggers).

Enforce the frozen Claims/Evidence invariants at the database, not in app/UI code:
- investigation raw labels (company_label, contact_label) are immutable;
- audit_event is append-only (no UPDATE/DELETE);
- source is an immutable versioned capture — no UPDATE/DELETE of a prior row
  (change = a new version row via supersedes_id);
- evidence is historical investigation material — append-only (no UPDATE/DELETE),
  so what the analyst originally saw is never silently rewritten.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0002_integrity_guards"
down_revision: str | None = "19b7bec01c76"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION arie_guard_raw_labels() RETURNS trigger AS $$
        BEGIN
            IF NEW.company_label IS DISTINCT FROM OLD.company_label THEN
                RAISE EXCEPTION 'company_label is immutable and cannot be overwritten';
            END IF;
            IF NEW.contact_label IS DISTINCT FROM OLD.contact_label THEN
                RAISE EXCEPTION 'contact_label is immutable and cannot be overwritten';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER trg_investigation_immutable_labels
            BEFORE UPDATE ON investigation
            FOR EACH ROW EXECUTE FUNCTION arie_guard_raw_labels();

        CREATE OR REPLACE FUNCTION arie_block_write() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION '% is append-only/immutable (% blocked)', TG_TABLE_NAME, TG_OP;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER trg_audit_event_append_only
            BEFORE UPDATE OR DELETE ON audit_event
            FOR EACH ROW EXECUTE FUNCTION arie_block_write();

        CREATE TRIGGER trg_source_immutable
            BEFORE UPDATE OR DELETE ON source
            FOR EACH ROW EXECUTE FUNCTION arie_block_write();

        CREATE TRIGGER trg_evidence_append_only
            BEFORE UPDATE OR DELETE ON evidence
            FOR EACH ROW EXECUTE FUNCTION arie_block_write();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_evidence_append_only ON evidence;")
    op.execute("DROP TRIGGER IF EXISTS trg_source_immutable ON source;")
    op.execute("DROP TRIGGER IF EXISTS trg_audit_event_append_only ON audit_event;")
    op.execute("DROP TRIGGER IF EXISTS trg_investigation_immutable_labels ON investigation;")
    op.execute("DROP FUNCTION IF EXISTS arie_block_write();")
    op.execute("DROP FUNCTION IF EXISTS arie_guard_raw_labels();")
