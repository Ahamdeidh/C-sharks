# Deployment

The application has a separate FastAPI backend and Vite frontend. Deploy both; the frontend needs the public backend URL at build time. These are provider-neutral starting steps, not a claim that a deployment has been performed.

## Backend: Render, Railway, or Fly.io

1. Create a Python service from this repository and set its working directory to `backend` (or configure equivalent paths from the repository root).
2. Install dependencies with `pip install -r requirements.txt`.
3. Start the service with `uvicorn main:app --host 0.0.0.0 --port $PORT` (use the provider's assigned port; if its command parser does not expand `$PORT`, use its documented port variable syntax).
4. Set `ENABLE_LIVE_HORIZONS=1` only if outbound access to JPL Horizons is desired. It is optional; the recorded fixture has limited date/location coverage. Do not set secrets unless a future integration requires them.
5. Ensure the deployed artifact includes `backend/data/` and the DEM subset. Set backend `ALLOWED_ORIGINS` to the comma-separated exact deployed frontend origins, e.g. `https://your-app.vercel.app`. The app currently uses `allow_credentials=False`; do not use `*` as a production default. Redeploy and verify preflight/API requests from the live frontend.
6. Check the provider health/logs and test the API URL directly before connecting the frontend.

## Frontend: Vercel or Netlify

1. Import the repository and use the repository root as the frontend project root (or configure the provider's base directory accordingly).
2. Build command: `npm run build`. Publish/output directory: `dist`.
3. Add the environment variable `VITE_API_BASE_URL` with the public backend base URL, for example `https://your-api.onrender.com` (no trailing slash is preferable). Vite embeds `VITE_*` variables at build time, so set it before each production build/redeploy.
4. Redeploy, open the site, and confirm the browser can reach the backend without a CORS error. Configure a custom frontend domain in the backend CORS allowlist as well if used.

## Configuration summary

| Variable | Where | Purpose |
|---|---|---|
| `VITE_API_BASE_URL` | Frontend build environment | Public base URL for the separate backend API; required for production frontend configuration. |
| `ENABLE_LIVE_HORIZONS=1` | Backend runtime environment (optional) | Opts into live JPL Horizons requests; otherwise use the available site/window-matched recorded fixtures. |
| `ALLOWED_ORIGINS` | Backend runtime environment | Comma-separated exact frontend HTTPS origins allowed by FastAPI CORS. |
| CORS allowed origin(s) | Backend configuration | Must include the exact HTTPS origin of each deployed frontend. Verify implementation/configuration before deployment; no deployment-specific CORS setup is assumed by this guide. |

No static JSON fallback or precomputed-snapshot mode is documented as available: use the backend API and surface its actual availability rather than presenting stale or fabricated results as live analysis.

## Remaining manual work

- Deploy backend and frontend, set `ALLOWED_ORIGINS` and `VITE_API_BASE_URL`, and verify the deployed API and CORS behavior. No production deployment was performed as part of these code changes.
- The Horizons fixtures were recorded and can be selected by matching coordinates; enable `ENABLE_LIVE_HORIZONS=1` only if desired and if the deployed host has outbound network access.
- No static precomputed-snapshot fallback was added. If required, design its stale-data labeling and update cadence before exposing it to judges; never represent snapshots as live results.
- Independently compare the DEM center-row/column anomaly with its original full LOLA source and reconcile the approximately 6,238 m raster pixel elevation against the fixture's 4,200 m observer altitude before using a single authoritative Shackleton site elevation.
