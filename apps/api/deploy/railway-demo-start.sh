#!/bin/sh
set -eu

uv run --no-sync python deploy/seed-demo-data.py
uv run --no-sync python -m arie_sentinel.jobs.worker &
exec uv run --no-sync uvicorn arie_sentinel.main:app --host 0.0.0.0 --port "${PORT:-8000}"
