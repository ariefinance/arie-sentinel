"""Official sanctions cache: refresh, coverage semantics, and screening gate."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from arie_sentinel.config import Settings
from arie_sentinel.models.enums import ScreeningState
from arie_sentinel.models.sanctions import SanctionsFeedState, SanctionsRecord
from arie_sentinel.providers.sanctions import OfficialSanctionsProvider
from arie_sentinel.services.investigations import _run_screening, create_investigation
from arie_sentinel.services.sanctions_cache import (
    coverage_report,
    load_sanctions_matcher,
    refresh_feeds,
)
from test_sanctions_feeds import OFAC, UK, UN

_SETTINGS = Settings(
    sanctions_ofac_url="https://ofac.test/SDN.XML",
    sanctions_un_url="https://un.test/consolidated.xml",
    sanctions_uk_url="https://uk.test/list.xml",
    sanctions_eu_url=None,
    sanctions_required_feeds="OFAC,UN,UK",
)

_BODIES = {
    "/SDN.XML": OFAC,
    "/consolidated.xml": UN,
    "/list.xml": UK,
}


def _mock_client(fail_path: str | None = None) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == fail_path:
            return httpx.Response(503, text="upstream down", request=request)
        return httpx.Response(200, content=_BODIES[path], request=request)

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_refresh_populates_cache_and_marks_feeds_fresh(db: Session) -> None:
    results = refresh_feeds(db, _SETTINGS, client=_mock_client())
    db.commit()
    assert {r.feed: r.status for r in results} == {"OFAC": "ok", "UN": "ok", "UK": "ok"}
    assert db.scalar(select(SanctionsRecord).where(SanctionsRecord.feed == "OFAC")) is not None
    report = coverage_report(db, _SETTINGS)
    assert report.is_complete
    assert set(report.fresh) == {"OFAC", "UN", "UK"}


def test_refresh_failure_retains_stale_records_and_marks_failed(db: Session) -> None:
    # Seed a prior UN cache, then a refresh where UN is down.
    db.add(
        SanctionsRecord(
            feed="UN",
            name="Prior Cached Entity",
            entity_type="entity",
            refreshed_at=datetime.now(UTC),
        )
    )
    db.commit()
    results = refresh_feeds(db, _SETTINGS, client=_mock_client(fail_path="/consolidated.xml"))
    db.commit()
    by_feed = {r.feed: r for r in results}
    assert by_feed["UN"].status == "failed"
    assert by_feed["OFAC"].status == "ok"
    # Stale UN records are retained, never wiped by a failed refresh.
    retained = db.scalars(select(SanctionsRecord).where(SanctionsRecord.feed == "UN")).all()
    assert [r.name for r in retained] == ["Prior Cached Entity"]
    # UN is a required feed and is now failed -> coverage is incomplete.
    report = coverage_report(db, _SETTINGS)
    assert not report.is_complete
    assert "UN" in report.stale_or_missing


def _seed_fresh_feeds(db: Session) -> None:
    for feed in ("OFAC", "UN", "UK"):
        db.add(
            SanctionsFeedState(
                feed=feed, status="ok", last_success_at=datetime.now(UTC), entity_count=1
            )
        )
    db.commit()


def _investigation(db: Session):
    return create_investigation(
        db,
        company_label="Testco Ltd",
        contact_label="Jane Roe",
        actor="analyst@example.test",
    )


def test_screening_no_clearance_when_coverage_incomplete(db: Session) -> None:
    inv = _investigation(db)
    _run_screening(db, inv, SimpleNamespace(screening=OfficialSanctionsProvider()))
    # No feeds cached -> required coverage incomplete -> never "no material match".
    assert inv.screening_state is None


def test_screening_no_material_match_only_when_coverage_complete(db: Session) -> None:
    _seed_fresh_feeds(db)
    inv = _investigation(db)
    _run_screening(db, inv, SimpleNamespace(screening=OfficialSanctionsProvider()))
    assert inv.screening_state is ScreeningState.NO_MATERIAL_MATCH


def test_screening_surfaces_potential_match_never_auto_confirms(db: Session) -> None:
    _seed_fresh_feeds(db)
    db.add(
        SanctionsRecord(
            feed="OFAC",
            name="Testco Ltd",
            entity_type="entity",
            refreshed_at=datetime.now(UTC),
        )
    )
    db.commit()
    inv = _investigation(db)
    _run_screening(db, inv, SimpleNamespace(screening=OfficialSanctionsProvider()))
    # A name hit is a POTENTIAL_MATCH requiring review — never an automatic confirmation.
    assert inv.screening_state is ScreeningState.POTENTIAL_MATCH


def test_load_matcher_reads_cached_records(db: Session) -> None:
    refresh_feeds(db, _SETTINGS, client=_mock_client())
    db.commit()
    provider, report = load_sanctions_matcher(db, _SETTINGS)
    assert isinstance(provider, OfficialSanctionsProvider)
    assert report.total_entities > 0
