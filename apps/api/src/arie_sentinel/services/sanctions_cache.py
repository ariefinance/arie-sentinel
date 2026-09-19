"""Official sanctions cache: refresh (download + parse + persist) and load-for-screening.

The cache is ordinary PostgreSQL (no Redis). ``refresh_feeds`` downloads each
configured official feed, parses it, and atomically replaces that feed's cached
records while recording per-feed state. A feed that fails to download/parse keeps
its previously cached records (stale data is retained, never wiped) and is marked
``failed`` so screening can treat it as not-fresh.

``load_sanctions_matcher`` builds an ``OfficialSanctionsProvider`` from the cache and
returns a coverage report. Screening may only report "no material match" when the
coverage report says every required feed is fresh and successful.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..models.sanctions import SanctionsFeedState, SanctionsRecord
from ..providers.base import ProviderError
from ..providers.sanctions import OfficialSanctionsProvider, SanctionedEntity
from ..providers.sanctions_feeds import download_feed, parse_feed


def _configured_feeds(settings: Settings) -> dict[str, str]:
    """Return {feed_name: url} for every feed that has a URL configured."""
    mapping = {
        "OFAC": settings.sanctions_ofac_url,
        "UN": settings.sanctions_un_url,
        "UK": settings.sanctions_uk_url,
        "EU": settings.sanctions_eu_url,
    }
    return {name: url for name, url in mapping.items() if url}


def required_feeds(settings: Settings) -> tuple[str, ...]:
    return tuple(
        f.strip().upper() for f in settings.sanctions_required_feeds.split(",") if f.strip()
    )


@dataclass(frozen=True)
class FeedRefreshResult:
    feed: str
    status: str  # ok | failed
    entity_count: int
    detail: str | None = None


@dataclass(frozen=True)
class CoverageReport:
    required: tuple[str, ...]
    fresh: tuple[str, ...]  # required feeds that are ok AND within max age
    stale_or_missing: tuple[str, ...]
    total_entities: int
    checked_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def is_complete(self) -> bool:
        return not self.stale_or_missing and bool(self.required)

    def limitation_text(self) -> str:
        return (
            "Sanctions screening coverage is incomplete: the required official feed(s) "
            f"{', '.join(self.stale_or_missing)} are not present and fresh in the cache. "
            "No 'no material match' clearance can be asserted until every required feed has "
            "been refreshed. Available feeds were still screened and any potential match is "
            "surfaced for analyst review."
        )


def _now() -> datetime:
    return datetime.now(UTC)


def refresh_feeds(
    session: Session,
    settings: Settings | None = None,
    *,
    client: httpx.Client | None = None,
    feeds: list[str] | None = None,
) -> list[FeedRefreshResult]:
    """Download, parse, and cache each configured feed. Returns per-feed results.

    On any per-feed failure the previously cached records are retained and the feed
    is marked ``failed`` — a refresh outage never silently empties the cache.
    """
    settings = settings or get_settings()
    configured = _configured_feeds(settings)
    targets = feeds or list(configured)
    owns_client = client is None
    client = client or httpx.Client(
        timeout=settings.provider_timeout_seconds, follow_redirects=True
    )
    results: list[FeedRefreshResult] = []
    required = set(required_feeds(settings))
    try:
        for name in targets:
            url = configured.get(name)
            state = session.get(SanctionsFeedState, name) or SanctionsFeedState(feed=name)
            state.last_attempt_at = _now()
            state.source_url = url
            if not url:
                state.status = "failed"
                state.detail = "no feed URL configured"
                session.merge(state)
                results.append(FeedRefreshResult(name, "failed", 0, state.detail))
                continue
            try:
                payload = download_feed(client, url, settings.sanctions_feed_max_bytes)
                entities = parse_feed(name, payload)
            except ProviderError as exc:
                state.status = "failed"
                state.detail = f"{type(exc).__name__}: {exc}"
                session.merge(state)
                session.flush()
                results.append(FeedRefreshResult(name, "failed", 0, state.detail))
                continue
            # Fail closed on an empty parse for REQUIRED feeds: a download that parses
            # to zero usable entities is an invalid refresh (a schema change or a
            # truncated/placeholder file), never a legitimate "empty sanctions list".
            # Retain the previously cached records and mark the feed failed so coverage
            # stays incomplete and NO_MATERIAL_MATCH cannot be asserted.
            if name in required and not entities:
                state.status = "failed"
                state.detail = (
                    "empty parse: download succeeded but zero usable entities were parsed "
                    "for a required feed; previous cache retained"
                )
                session.merge(state)
                session.flush()
                results.append(FeedRefreshResult(name, "failed", 0, state.detail))
                continue
            # Atomically replace this feed's cached records.
            session.execute(delete(SanctionsRecord).where(SanctionsRecord.feed == name))
            refreshed_at = _now()
            for entity in entities:
                session.add(
                    SanctionsRecord(
                        feed=name,
                        profile_id=entity.profile_id,
                        name=entity.name,
                        entity_type=entity.entity_type,
                        aliases=list(entity.aliases),
                        birth_dates=list(entity.birth_dates),
                        countries=list(entity.countries),
                        identifiers=list(entity.identifiers),
                        refreshed_at=refreshed_at,
                    )
                )
            state.status = "ok"
            state.detail = None
            state.entity_count = len(entities)
            state.last_success_at = refreshed_at
            session.merge(state)
            session.flush()
            results.append(FeedRefreshResult(name, "ok", len(entities)))
    finally:
        if owns_client:
            client.close()
    return results


def _load_records(session: Session) -> list[SanctionedEntity]:
    rows = session.scalars(select(SanctionsRecord)).all()
    return [
        SanctionedEntity(
            name=row.name,
            source_list=row.feed,
            entity_type=row.entity_type,
            aliases=tuple(row.aliases or ()),
            birth_dates=tuple(row.birth_dates or ()),
            countries=tuple(row.countries or ()),
            identifiers=tuple(row.identifiers or ()),
            profile_id=row.profile_id,
        )
        for row in rows
    ]


def coverage_report(session: Session, settings: Settings | None = None) -> CoverageReport:
    settings = settings or get_settings()
    req = required_feeds(settings)
    max_age = timedelta(hours=settings.sanctions_cache_max_age_hours)
    cutoff = _now() - max_age
    states = {s.feed: s for s in session.scalars(select(SanctionsFeedState)).all()}
    fresh: list[str] = []
    stale: list[str] = []
    for feed in req:
        state = states.get(feed)
        if (
            state is not None
            and state.status == "ok"
            and state.last_success_at is not None
            and state.last_success_at >= cutoff
        ):
            fresh.append(feed)
        else:
            stale.append(feed)
    total = sum(s.entity_count for s in states.values() if s.status == "ok")
    return CoverageReport(
        required=req,
        fresh=tuple(fresh),
        stale_or_missing=tuple(stale),
        total_entities=total,
    )


def load_sanctions_matcher(
    session: Session, settings: Settings | None = None
) -> tuple[OfficialSanctionsProvider, CoverageReport]:
    """Build a screening provider from the cache and report required-feed coverage."""
    settings = settings or get_settings()
    provider = OfficialSanctionsProvider()
    provider.load_entities(_load_records(session))  # loads whatever is cached (may be empty)
    return provider, coverage_report(session, settings)
