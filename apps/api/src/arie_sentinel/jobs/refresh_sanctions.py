"""Scheduled official-sanctions refresh entrypoint.

Run on a schedule (cron / systemd timer / container sidecar), e.g. daily:

    python -m arie_sentinel.jobs.refresh_sanctions

Downloads every configured official feed, parses it, and refreshes the local
PostgreSQL cache. A per-feed failure is logged and leaves that feed's previously
cached records intact; it never empties the cache. No Redis / Celery — this is a
plain, independently-runnable process.
"""

from __future__ import annotations

import logging

from ..config import get_settings
from ..db import session_scope
from ..services.sanctions_cache import refresh_feeds

logger = logging.getLogger("arie_sentinel.sanctions_refresh")


def main() -> int:
    settings = get_settings()
    with session_scope() as session:
        results = refresh_feeds(session, settings)
    failures = 0
    for result in results:
        if result.status == "ok":
            logger.info("sanctions feed %s: %d entities", result.feed, result.entity_count)
        else:
            failures += 1
            logger.warning("sanctions feed %s failed: %s", result.feed, result.detail)
    logger.info("sanctions refresh complete: %d feed(s), %d failure(s)", len(results), failures)
    return 1 if failures else 0


if __name__ == "__main__":  # pragma: no cover - operational entrypoint
    logging.basicConfig(level=logging.INFO)
    raise SystemExit(main())
