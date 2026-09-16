"""Live-intelligence candidates and screening review fields."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_live_intelligence"
down_revision: str | None = "0002_integrity_guards"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("auditaction", "audit_event", type_="check")
    op.create_check_constraint(
        "auditaction",
        "audit_event",
        "action IN ('INVESTIGATION_CREATED','REQUEST_CLARIFICATION','CLARIFICATION_SUPPLIED',"
        "'RESOLVE_IDENTITY','LINK_COUNTERPARTY','CONFIRM_FINDING','DISMISS_FINDING',"
        "'REQUEST_INFORMATION','ADD_NOTE','FINALISE_REPORT','STATE_CHANGE',"
        "'IMPORT_BATCH_CREATED','REVIEW_SCREENING','REVIEW_FINDING')",
    )
    op.create_table(
        "entity_candidate",
        sa.Column("entity_candidate_id", sa.Uuid(), nullable=False),
        sa.Column("investigation_id", sa.Uuid(), nullable=False),
        sa.Column("legal_name", sa.String(512), nullable=False),
        sa.Column("jurisdiction", sa.String(64)),
        sa.Column("registry_class", sa.String(64)),
        sa.Column("registry_id", sa.String(128)),
        sa.Column("legal_status", sa.String(64)),
        sa.Column("registered_address", sa.Text()),
        sa.Column("incorporation_date", sa.String(32)),
        sa.Column("lei", sa.String(20)),
        sa.Column("alternative_names", postgresql.JSONB()),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("source_ref", sa.Text()),
        sa.Column("retrieved_at", sa.DateTime(), nullable=False),
        sa.Column("match_basis", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["investigation_id"], ["investigation.investigation_id"]),
        sa.PrimaryKeyConstraint("entity_candidate_id"),
    )
    op.add_column("screening_result", sa.Column("matched_profile_id", sa.String(256)))
    op.add_column("screening_result", sa.Column("match_score", sa.Float()))
    op.add_column("screening_result", sa.Column("match_explanation", postgresql.JSONB()))
    op.add_column("screening_result", sa.Column("matched_identifiers", postgresql.JSONB()))
    op.add_column("screening_result", sa.Column("datasets", postgresql.JSONB()))
    op.add_column("screening_result", sa.Column("analyst_disposition", sa.String(32)))
    op.add_column("screening_result", sa.Column("analyst_rationale", sa.Text()))
    op.execute(
        """
        CREATE OR REPLACE FUNCTION arie_guard_ai_evidence() RETURNS trigger AS $$
        BEGIN
            IF NEW.extracted_by LIKE 'model%' AND NEW.extraction_confidence = 'AUTHORITATIVE' THEN
                RAISE EXCEPTION 'AI/model output cannot be authoritative evidence';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        CREATE TRIGGER trg_evidence_ai_boundary
            BEFORE INSERT ON evidence
            FOR EACH ROW EXECUTE FUNCTION arie_guard_ai_evidence();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_evidence_ai_boundary ON evidence")
    op.execute("DROP FUNCTION IF EXISTS arie_guard_ai_evidence()")
    op.drop_column("screening_result", "analyst_rationale")
    op.drop_column("screening_result", "analyst_disposition")
    op.drop_column("screening_result", "datasets")
    op.drop_column("screening_result", "matched_identifiers")
    op.drop_column("screening_result", "match_explanation")
    op.drop_column("screening_result", "match_score")
    op.drop_column("screening_result", "matched_profile_id")
    op.drop_table("entity_candidate")
    op.drop_constraint("auditaction", "audit_event", type_="check")
    op.create_check_constraint(
        "auditaction",
        "audit_event",
        "action IN ('INVESTIGATION_CREATED','REQUEST_CLARIFICATION','CLARIFICATION_SUPPLIED',"
        "'RESOLVE_IDENTITY','LINK_COUNTERPARTY','CONFIRM_FINDING','DISMISS_FINDING',"
        "'REQUEST_INFORMATION','ADD_NOTE','FINALISE_REPORT','STATE_CHANGE',"
        "'IMPORT_BATCH_CREATED')",
    )
