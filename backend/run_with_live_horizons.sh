#!/usr/bin/env bash
# Start FastAPI locally with live NASA/JPL Horizons lookups enabled.
# Override ENABLE_LIVE_HORIZONS=0 to disable, or BIND_HOST for deployment.
set -euo pipefail
cd "$(dirname "$0")"
export ENABLE_LIVE_HORIZONS="${ENABLE_LIVE_HORIZONS:-1}"
exec python -m uvicorn main:app --host "${BIND_HOST:-127.0.0.1}" --port "${PORT:-8000}"
