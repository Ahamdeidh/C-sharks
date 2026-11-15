#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

command -v python3 >/dev/null 2>&1 || { echo 'Python 3 is required.' >&2; exit 1; }
command -v node >/dev/null 2>&1 || { echo 'Node.js is required.' >&2; exit 1; }
command -v npm >/dev/null 2>&1 || { echo 'npm is required.' >&2; exit 1; }

if [[ ! -x .venv/bin/python ]]; then
  python3 -m venv .venv
fi
export PATH="$ROOT/.venv/bin:$PATH"
if ! .venv/bin/python -c 'import fastapi, uvicorn, numpy, requests, httpx, shapefile, rasterio, tifffile' >/dev/null 2>&1; then
  .venv/bin/python -m pip install --upgrade pip
  .venv/bin/python -m pip install -r backend/requirements.txt
fi
if [[ ! -x node_modules/.bin/vite ]]; then
  npm ci
fi

export ENABLE_LIVE_HORIZONS=1
export VITE_API_BASE_URL="${VITE_API_BASE_URL:-http://127.0.0.1:8000}"
./backend/run_with_live_horizons.sh &
BACKEND_PID=$!
cleanup() {
  kill "$BACKEND_PID" 2>/dev/null || true
  wait "$BACKEND_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

printf 'Waiting for backend at %s ...\n' "$VITE_API_BASE_URL"
if ! .venv/bin/python - "$VITE_API_BASE_URL" <<'PY'
import sys, time, requests
base = sys.argv[1].rstrip('/')
for _ in range(45):
    try:
        r = requests.get(base + '/openapi.json', timeout=2)
        if r.ok:
            print('Backend is ready.')
            raise SystemExit(0)
    except requests.RequestException:
        pass
    time.sleep(1)
print('Backend did not become ready in 45 seconds. Check its startup output above.', file=sys.stderr)
raise SystemExit(1)
PY
then
  exit 1
fi

echo 'Starting frontend at http://127.0.0.1:3000 (press Ctrl+C to stop both services).'
npm run dev -- --host 127.0.0.1
