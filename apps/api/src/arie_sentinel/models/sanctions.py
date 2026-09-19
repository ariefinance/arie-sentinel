"""Official sanctions cache — a lightweight PostgreSQL store for ingested feeds.

No Redis / external cache: the normalized sanctions entities and per-feed refresh
state live in ordinary tables. Screening reads this cache; it never calls a paid
aggregator, and it only reports "no material match" when every required feed has a
fresh, successful refresh recorded here.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, uuid_pk


class SanctionsFeedState(Base, TimestampMixin):
    """Per-feed refresh bookkeeping (one row per official feed)."""

    __tablename__ = "sanctions_feed_state"

    feed: Mapped[str] = mapped_column(String(16), primary_key=True)  # OFAC | UN | UK | EU
    # never_refreshed | ok | failed
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="never_refreshed")
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    entity_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source_url: Mapped[str | None] = mapped_column(Text)
    detail: Mapped[str | None] = mapped_column(Text)


class SanctionsRecord(Base):
    """One normalized sanctioned entity from an official feed."""

    __tablename__ = "sanctions_record"

    record_id: Mapped[uuid.UUID] = uuid_pk()
    feed: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    profile_id: Mapped[str | None] = mapped_column(String(256))
    name: Mapped[str] = mapped_column(String(1024), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(16), nullable=False, default="entity")
    aliases: Mapped[list[str] | None] = mapped_column(JSONB)
    birth_dates: Mapped[list[str] | None] = mapped_column(JSONB)
    countries: Mapped[list[str] | None] = mapped_column(JSONB)
    identifiers: Mapped[list[str] | None] = mapped_column(JSONB)
    extra: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    refreshed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
