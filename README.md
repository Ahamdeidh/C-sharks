# Lunar Landing Site Navigator

An engineering and mission-planning prototype for exploring lunar south-polar landing-site conditions. It combines terrain and ephemeris inputs with reference/archive material; it is not a flight-certification tool.

## Data scope and limits

- **Regional LOLA-labelled DEM:** `backend/data/dem/LDEM_80S_80MPP_ADJ.TIF` is a central **601 × 601** raster at a nominal **80 m/pixel**, covering approximately **48 × 48 km**. It is a subset, not the full tile.
- **Additional 5 m DEM assets:** four challenge tiles and their sidecars are retained under `backend/data/challenge_package/dem/Site01..Site11/`. Runtime selects a tile only when the point lies inside its declared bounds and its sample agrees with the regional raster within a 100 m screening threshold. At the archived Site01 sample (−89.4°, 222°), the 5 m and regional elevations differ by about **2,339 m**, so it is **not activated**; the runtime falls back to the regional DEM and exposes the cross-check. This discrepancy needs source/datum/geolocation investigation, not normalization. The Site04 sample at the Shackleton preset (−89.9°, 0°) also differs by about 5,646 m, so it is likewise withheld. Three tiles do not provide uncertainty rasters; the two Site01 uncertainty TIFFs are retained as archive assets but are not ingested into runtime risk calculations because validated companion sidecars and uncertainty propagation are not implemented.
- **JPL Horizons:** the original short fixtures remain. Additional raw-response fixtures cover **2025–2028, hourly** at Malapert A, Nobile Region, and the source-labelled CLPS Shackleton Connecting Ridge coordinates; see `backend/data/challenge_package/manifest_southern_polar.json`. The CLPS fixture coordinates (−89.63°, 132.32°) are not the existing Connecting Ridge preset (−89.4°, 222°). Observer altitude in those requests is **0 km**; when it differs from the preset ground-elevation baseline by more than 100 m, only raw ephemeris is exposed and terrain-fused KPIs are withheld. EOP coverage notes are included in the manifest. Live queries remain opt-in with `ENABLE_LIVE_HORIZONS=1`; no extrapolation is presented as observed.
- **Scale and hazard limits:** gradients are reported at source resolution. The system does not infer 15 m landing-pad slope from 80 m pixels using an assumed Hurst exponent, and it does not report a clean-pad probability without a local, georeferenced boulder inventory. These models are screening-only, not flight certification.
- **Regional catalog:** `backend/data/reference/lunar_catalog_v2.json` contains archive records (336 rasters, 141 PSR polygons, 21 areas). Its own provenance warning says the archives were user-supplied and upstream provenance/field definitions are unverified. Do not attribute it to NASA without independent evidence.
- **Curated assumptions:** model inputs such as `rock_abundance_fraction` are curated assumptions, not site-level measurements extracted from Diviner. Interpret risk outputs accordingly.
- Preset summary values and model estimates are not certified mission predictions. See [REFERENCES.md](REFERENCES.md) for sources and provenance notes.

## Architecture

- Backend: FastAPI service in `backend/`.
- Frontend: React/Vite application in the repository root.
- Deployment requires the frontend to point to a separately deployed backend using `VITE_API_BASE_URL`; see [`DEPLOYMENT.md`](DEPLOYMENT.md).

## Run locally

### One-command startup

Install Python 3 and Node.js/npm, then run the launcher for your operating system. It creates a local Python virtual environment and installs dependencies if needed. Live JPL Horizons requests are enabled for the backend; no Horizons API key is required.

Linux/macOS:

```bash
chmod +x run_project.sh
./run_project.sh
```

Windows: double-click `run_project.bat`. It opens separate backend and frontend terminal windows. Then open `http://127.0.0.1:3000`.

To stop on Linux/macOS, press `Ctrl+C` in the launcher terminal. On Windows, close both service windows. The backend launcher `backend/run_with_live_horizons.sh` can also be run on its own after backend dependencies are installed.

The Vite frontend uses `VITE_API_BASE_URL=http://127.0.0.1:8000` locally. `ENABLE_LIVE_HORIZONS=1` must be present in the backend process environment; a root `.env` file by itself is not loaded by Uvicorn. Do not put secrets in any `VITE_` variable. Horizons is a public NASA/JPL API and does not require a key.

### Manual startup

Backend, from the project root:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r backend/requirements.txt
cd backend
ENABLE_LIVE_HORIZONS=1 ../.venv/bin/python -m uvicorn main:app --reload --port 8000
```

Frontend, in a second terminal from the project root:

```bash
npm ci
npm run dev -- --host 127.0.0.1
```

## Verification results

After integration, **98 backend tests passed** and **40 frontend tests passed**. `npm run build` completed successfully. These are local sandbox results, not a production deployment or flight qualification. The analytic verification suite checks implementation invariants and model consistency; it is not independent site validation.

Run frontend checks with:

```bash
npm test -- --run
npm run build
```

For DEM file details and limits, see [`backend/data/dem/README.md`](backend/data/dem/README.md).

## DEM anomaly and elevation notes
The 601 × 601 TIFF is stored without an embedded GeoTIFF geotransform; the project applies its documented centered polar-stereographic sidecar mapping. Rows 295–305 around column 300 contain valid but varying elevations, not a constant line of missing values. In the local comparison of the center column against its two neighbors, the residual median is about −118 m and the 95th-percentile absolute difference about 684 m. This file alone cannot classify the variation as a processing artifact or geologic feature; no original full-tile comparison or processing provenance is bundled. Treat it cautiously pending comparison with the original LOLA source.

At nominal Shackleton coordinates (−89.9°, 0°), the bundled DEM pixel is approximately 6,238 m relative to its stated reference sphere, while the recorded Horizons query metadata specifies a 4,200 m observer altitude. These source values are not reconciled; the fixture keeps its recorded 4,200 m input. Do not combine them as one certified site elevation.
