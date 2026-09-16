#!/bin/sh
set -eu

# Railway private networking resolves service names over IPv6. Bind Uvicorn to
# the dual-stack wildcard so Nginx can use the private service hostname without
# falling back after a refused IPv6 connection.
uv run --no-sync python -m arie_sentinel.jobs.worker &
exec uv run --no-sync uvicorn arie_sentinel.main:app --host :: --port "${PORT:-8000}"
