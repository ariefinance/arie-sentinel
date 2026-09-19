#!/bin/sh
set -eu

uv run --no-sync python deploy/seed-demo-data.py

# Keep the official sanctions cache current without a separate Railway cron service.
# Refresh immediately on container start, then once every 24 hours. A refresh failure
# must not take down the management-demo API; screening itself remains fail-closed
# through the cache coverage checks.
(
  uv run --no-sync python -m arie_sentinel.jobs.refresh_sanctions || true
  while sleep 86400; do
    uv run --no-sync python -m arie_sentinel.jobs.refresh_sanctions || true
  done
) &

uv run --no-sync python -m arie_sentinel.jobs.worker &
exec uv run --no-sync uvicorn arie_sentinel.main:app --host 0.0.0.0 --port "${PORT:-8000}"
