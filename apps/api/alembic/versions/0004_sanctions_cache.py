"""Official sanctions cache: normalized records + per-feed refresh state."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_sanctions_cache"
down_revision: str | None = "0003_live_intelligence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sanctions_feed_state",
        sa.Column("feed", sa.String(16), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="never_refreshed"),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True)),
        sa.Column("last_success_at", sa.DateTime(timezone=True)),
        sa.Column("entity_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("source_url", sa.Text()),
        sa.Column("detail", sa.Text()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("feed"),
    )
    op.create_table(
        "sanctions_record",
        sa.Column("record_id", sa.Uuid(), nullable=False),
        sa.Column("feed", sa.String(16), nullable=False),
        sa.Column("profile_id", sa.String(256)),
        sa.Column("name", sa.String(1024), nullable=False),
        sa.Column("entity_type", sa.String(16), nullable=False, server_default="entity"),
        sa.Column("aliases", postgresql.JSONB()),
        sa.Column("birth_dates", postgresql.JSONB()),
        sa.Column("countries", postgresql.JSONB()),
        sa.Column("identifiers", postgresql.JSONB()),
        sa.Column("extra", postgresql.JSONB()),
        sa.Column("refreshed_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("record_id"),
    )
    op.create_index("ix_sanctions_record_feed", "sanctions_record", ["feed"])


def downgrade() -> None:
    op.drop_index("ix_sanctions_record_feed", table_name="sanctions_record")
    op.drop_table("sanctions_record")
    op.drop_table("sanctions_feed_state")
