"""
=============================================================================
LUNAR LANDING SITE NAVIGATOR - FASTAPI BACKEND  v1.5.0
NASA Space Apps Challenge
-----------------------------------------------------------------------------
Backend service for Lunar South Pole landing site evaluation.
Integrates modular services for:
- JPL Horizons Ephemeris queries (Apparent Azimuth and Elevation)
- Verified NASA/GSFC LRO LOLA DEM (`LDEM_80S_80MPP_ADJ.TIF`, 80 m/px) ray-tracing
- Geodetic Control-Point Verification (6 IAU/LOLA South Pole landmarks)
- Bidirectional Pad-Scale Slope, Boulder Clearance, Regolith Bearing, Plume-Surface
  Interaction (PSI), and NASA DSN 34m X-Band RF Link Budget (`landing_risk_service`)
- 360° Horizon Panorama, Sunset/Earthset Countdowns & Solar Array Geometry
- Multi-Program Comparator (Apollo, CLPS, ISRO, CNSA, CSA, Artemis III)
- Provenance and methodology audit tracking

NOTE: Synthetic Demo fabrication is disabled by default for scientific integrity.
When verified DEM and JPL Horizons ephemeris cover the site, the engine returns
`terrain_aware` (`data_source='real_engine'`, `is_demo=False`).
=============================================================================
"""

import json
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

try:
    from pydantic import field_validator
except ImportError:
    from pydantic import validator as _pydantic_v1_validator

    def field_validator(*fields: str, **kwargs: Any):
        return _pydantic_v1_validator(*fields, **kwargs)

from services.simulation_engine import SimulationEngine, PREDEFINED_SITES
from services.impact_brief_service import build_decision_brief
from services.challenge_alignment_service import build_challenge_alignment
from services.mission_design_lab_service import build_design_lab
from services.verification_suite import run_benchmarks
from services.judge_evidence_service import build_judge_evidence_pack
from services.horizon_and_ops_service import compute_operational_windows
from services.landing_risk_service import evaluate_landing_site_risk

app = FastAPI(
    title="Lunar Landing Site Navigator API",
    description="Backend service for Lunar South Pole landing evaluation (LOLA DEM & JPL Horizons)",
    version="1.5.0"
)

# Instantiate simulation engine orchestrator
simulation_engine = SimulationEngine()

# ---------------------------------------------------------------------------
# CORS — restricted to origins configured via ALLOWED_ORIGINS env var.
# ---------------------------------------------------------------------------
raw_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173"
)
allowed_origins = [orig.strip() for orig in raw_origins.split(",") if orig.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Accept"],
)

# ---------------------------------------------------------------------------
# Global exception handler — returns safe JSON for unexpected errors
# ---------------------------------------------------------------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An unexpected server error occurred. Please verify simulation inputs or server logs.",
            "error_type": type(exc).__name__
        }
    )

# ---------------------------------------------------------------------------
# PYDANTIC SCHEMAS
# ---------------------------------------------------------------------------
class SimulationRequest(BaseModel):
    site_id: str = Field(..., min_length=1, max_length=50, description="Candidate site ID")
    lat: float = Field(..., ge=-90.0, le=-80.0, description="Lunar South Pole Latitude (-90.0 to -80.0)")
    lon: float = Field(..., ge=-180.0, le=360.0, description="Lunar Longitude in degrees")
    start_time: str = Field(..., description="Mission start ISO 8601 UTC timestamp (must include timezone info or trailing Z)")
    mission_duration_days: int = Field(..., ge=1, le=60, description="Mission duration in days (1 to 60)")
    timestep_hours: int = Field(..., ge=1, le=24, description="Simulation resolution step in hours (1 to 24)")
    antenna_height_m: float = Field(..., ge=0.0, le=20.0, description="Lander antenna mast height in meters")
    los_margin_deg: float = Field(..., ge=0.0, le=5.0, description="Line-of-sight elevation safety margin in degrees")
    demo_mode: bool = Field(default=False, description="Legacy flag; synthetic Demo fabrication is disabled in scientific mode")

    @field_validator("start_time")
    def validate_iso_timestamp(cls, v: str) -> str:
        try:
            cleaned = v.replace("Z", "+00:00")
            dt = datetime.fromisoformat(cleaned)
            if dt.tzinfo is None:
                raise ValueError("Timestamp must include timezone (e.g. 'Z' or '+02:00')")
            return v
        except Exception as e:
            raise ValueError(
                f"start_time must be a valid timezone-aware ISO 8601 timestamp "
                f"(e.g. '2026-11-14T12:00:00Z' or '2026-11-14T14:00:00+02:00'). Error: {e}"
            )

class MetricKPIs(BaseModel):
    avg_illumination_pct: Optional[float] = Field(None, description="Average solar illumination [0-100%]")
    dte_connection_pct: Optional[float] = Field(None, description="Average Direct-to-Earth geometric line-of-sight visibility [0-100%]")
    geometric_dte_visibility_pct: Optional[float] = Field(None, description="Average Direct-to-Earth geometric line-of-sight visibility [0-100%]")
    longest_continuous_darkness_hours: Optional[float] = Field(None, description="Longest continuous period of zero/penumbral solar illumination in hours")
    longest_earth_blackout_hours: Optional[float] = Field(None, description="Longest continuous period of Earth geometric line-of-sight blockage in hours")
    max_amsi: Optional[str] = Field(None, description="Average Maximum Shadow Intensity descriptor")
    avg_asia_hours: Optional[float] = Field(None, description="Average Shadow Interval Area window in hours")
    slope_avg_deg: Optional[float] = Field(None, description="Bidirectional DEM terrain slope in degrees")
    composite_score: Optional[float] = Field(None, description="Overall suitability rating out of 5.0 (design index, not official NASA score)")
    composite_score_note: Optional[str] = Field(None, description="Discloses design choice weights and non-official status")
    landing_hazards_disclaimer: Optional[str] = Field(None, description="Notice regarding terrain-aware scope and engineering screening models")
    tradeoffs: Optional[Dict[str, Any]] = Field(None, description="Site-specific advantages, downsides, and data quality notes")
    kpis_provenance: Optional[Dict[str, Any]] = Field(None, description="Explicit per-metric source category and resolution limitation")

class TimelinePoint(BaseModel):
    timestamp: str = Field(..., description="ISO 8601 UTC timestamp for this time step")
    step_index: int = Field(..., description="Sequential step index (1-based)")
    elapsed_hours: float = Field(..., description="Elapsed hours from mission start")
    sol_day: float = Field(..., description="Elapsed days from start")
    illumination_pct: float = Field(..., description="Solar illumination percentage")
    dte_connection_pct: float = Field(..., description="Direct-to-Earth line of sight availability percentage")
    sun_elevation_deg: Optional[float] = Field(None, description="Solar apparent elevation angle in degrees")
    sun_azimuth_deg: Optional[float] = Field(None, description="Solar apparent azimuth angle in degrees clockwise from North")
    earth_elevation_deg: Optional[float] = Field(None, description="Earth apparent elevation angle in degrees")
    earth_azimuth_deg: Optional[float] = Field(None, description="Earth apparent azimuth angle in degrees clockwise from North")

class SimulationResponse(BaseModel):
    status: str = Field(..., description="'terrain_aware', 'terrain_benchmark', or 'engine_pending'")
    status_message: str = Field(..., description="Human-readable explanation of status and data source")
    data_source: str = Field(..., description="'real_engine', 'synthetic_terrain_benchmark', or 'none'")
    is_demo: bool = Field(..., description="Flag indicating if results use a synthetic benchmark DEM")
    inputs_used: Dict[str, Any] = Field(..., description="Exact normalized input parameters evaluated")
    coordinate_mismatch: Optional[str] = Field(None, description="Warning if submitted lat/lon differs from registered site coordinates")
    units: Dict[str, str] = Field(default_factory=lambda: {
        "illumination": "percentage (0-100%)",
        "dte_connection": "geometric line-of-sight visibility percentage (0-100%).",
        "longest_continuous_darkness": "hours of unbroken shadow",
        "longest_earth_blackout": "hours of unbroken Earth terrain occultation",
        "antenna_height": "meters",
        "los_margin": "degrees",
        "elevation": "meters relative to 1737.4 km reference sphere",
        "timestep": "hours",
        "duration": "days"
    })
    kpis: Optional[MetricKPIs] = None
    timeline: List[TimelinePoint] = Field(default_factory=list)
    total_time_steps: int = 0
    ephemeris_check: Optional[Dict[str, Any]] = Field(None, description="Real NASA JPL Horizons Sun/Earth apparent angles for the requested time grid.")
    validation_report: Optional[Dict[str, Any]] = Field(None, description="Scientific and technical quality gate.")
    reference_kpis: Optional[Dict[str, Any]] = Field(None, description="KPIs from real Horizons angles with a smooth-sphere horizon (no terrain).")
    terrain_info: Optional[Dict[str, Any]] = Field(None, description="DEM ingestion report, horizon-mask summary, geodetic control verification, and bidirectional pad-scale slope.")
    landing_risk_assessment: Optional[Dict[str, Any]] = Field(None, description="Physics-based pad-scale slope, boulder clearance, regolith Terzaghi bearing, plume-surface interaction, and DSN 34m X-band RF link budget.")
    provenance: Optional[Dict[str, Any]] = Field(None, description="Full audit provenance and methodology metadata")
    generated_at: str

# ---------------------------------------------------------------------------
# ENDPOINTS
# ---------------------------------------------------------------------------
@app.get("/api/v1/status")
def get_service_status():
    """Returns API health, verified LOLA DEM readiness, and scientific integrity mode."""
    dem_check = simulation_engine.dem_svc.check_local_dem_availability()
    kernel_check = simulation_engine.spice_status.evaluate_kernel_coverage()
    verified_dem, dem_report = simulation_engine._verified_dem()

    return {
        "service": "Lunar Landing Site Navigator API",
        "version": "1.5.0",
        "system_status": "online",
        "real_calculation_engine": {
            "status": "terrain_engine_ready" if verified_dem else "pending_integration",
            "reference_mode": "real Horizons angles with smooth-sphere horizon (reference_kpis) is active alongside DEM ray-tracing",
            "calculation_pipeline_connected": verified_dem is not None,
            "dem_verification": dem_report,
            "lola_dem_ingested": verified_dem is not None,
            "dem_status": dem_check["status_message"],
            "spice_kernels_ready": kernel_check["all_kernels_available"],
            "kernel_status": kernel_check["status_message"],
            "horizons_api_client": "active",
            "message": (
                f"Verified NASA LRO LOLA DEM ({verified_dem.meta['product_id']}, {verified_dem.meta['resolution_m_per_px']} m/px) is active and connected to 360-deg horizon ray-tracing, geodetic control-point verification, and bidirectional pad-scale slope extraction."
                if verified_dem is not None
                else "No verified LOLA DEM is currently loaded in backend/data/dem/; smooth-sphere reference_kpis remain active."
            ),
        },
        "demo_mode_available": False,
        "scientific_integrity_policy": "Synthetic Demo fabrication is disabled; only verified terrain_aware or real ephemeris reference results are returned.",
        "default_mode": "strict_scientific (real LOLA DEM + JPL Horizons engine)",
        "cors_allowed_origins": allowed_origins
    }

@app.get("/api/v1/sites")
def list_candidate_sites():
    """Returns registered Artemis candidate landing zones with real lunar coordinates and explicit illustrative-estimate disclosures."""
    return PREDEFINED_SITES

@app.get("/api/v1/reference/landing-sites")
def get_reference_landing_sites():
    """Returns user-supplied archive-derived lunar landing-site attributes and provenance."""
    catalog_path = Path(__file__).parent / "data" / "reference" / "lunar_candidate_sites.json"
    if not catalog_path.is_file():
        raise HTTPException(status_code=503, detail="Reference data catalog is not installed.")
    try:
        return json.loads(catalog_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raise HTTPException(status_code=503, detail="Reference data catalog could not be read.")

@app.get("/api/v1/reference/catalog-v2")
def get_reference_catalog_v2():
    """Returns regional raster summaries, PSR polygons, validation and source cautions."""
    catalog_path = Path(__file__).parent / "data" / "reference" / "lunar_catalog_v2.json"
    if not catalog_path.is_file():
        raise HTTPException(status_code=503, detail="Reference catalog v2 is not installed.")
    try:
        return json.loads(catalog_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raise HTTPException(status_code=503, detail="Reference catalog v2 could not be read.")

@app.get("/api/v1/mission/decision-brief")
def get_mission_decision_brief():
    """Returns an evidence-first regional triage brief, never a landing certificate."""
    try:
        return build_decision_brief()
    except (OSError, json.JSONDecodeError, KeyError) as exc:
        raise HTTPException(status_code=503, detail=f"Mission decision brief is unavailable: {exc}")

@app.get("/api/v1/challenge/alignment")
def get_challenge_alignment():
    """Returns a traceability matrix for challenge goals, features, data roles, and gaps."""
    return build_challenge_alignment()

@app.get("/api/v1/mission/design-lab")
def get_mission_design_lab():
    """Returns creative counterfactual mission-priority scenarios with explainable scores."""
    return build_design_lab()

@app.get("/api/v1/mission/horizon-ops")
def get_mission_horizon_ops(
    antenna_height_m: float = 6.0,
    los_margin_deg: float = 0.25,
    step_hours: int = 2,
):
    """Returns 360-deg horizon skyplot points, sunset/Earthset countdown status, solar array geometry, schedule-slip sensitivity, and multi-program comparator."""
    return compute_operational_windows(
        antenna_height_m=max(0.0, min(20.0, antenna_height_m)),
        los_margin_deg=max(0.0, min(5.0, los_margin_deg)),
        step_hours=max(1, min(12, step_hours)),
    )

@app.get("/api/v1/mission/landing-risk")
def get_mission_landing_risk(
    site_id: str = "shackleton",
    lat: float = -89.9,
    lon: float = 0.0,
    antenna_height_m: float = 6.0,
    los_margin_deg: float = 0.25,
    lander_mass_kg: float = 1850.0,
    lander_max_tilt_deg: float = 12.0,
    lander_belly_clearance_m: float = 0.65,
    descent_thrust_n: float = 15000.0,
    rf_tx_power_w: float = 15.0,
    rf_data_rate_mbps: float = 2.0,
    strict_field_certification_only: bool = False,
):
    """Returns physics-based pad-scale bidirectional slope, boulder clearance, regolith Terzaghi bearing capacity, plume-surface interaction, and DSN 34m X-band RF link budget."""
    return evaluate_landing_site_risk(
        site_id=site_id,
        lat=lat,
        lon=lon,
        antenna_height_m=antenna_height_m,
        los_margin_deg=los_margin_deg,
        lander_mass_kg=lander_mass_kg,
        lander_max_tilt_deg=lander_max_tilt_deg,
        lander_belly_clearance_m=lander_belly_clearance_m,
        descent_thrust_n=descent_thrust_n,
        rf_tx_power_w=rf_tx_power_w,
        rf_data_rate_mbps=rf_data_rate_mbps,
        strict_field_certification_only=strict_field_certification_only,
    )

@app.get("/api/v1/validation/benchmarks")
def get_validation_benchmarks():
    """Runs closed-form, geodetic control-point, and DEM integrity benchmarks (cached)."""
    return run_benchmarks()

@app.get("/api/v1/judge/evidence-pack")
def get_judge_evidence_pack():
    """Returns one traceable walkthrough for judging impact, creativity, validity, relevance, and presentation."""
    return build_judge_evidence_pack()

@app.get("/api/v1/provenance")
def get_provenance():
    """Returns complete data source specifications, documentation URLs, and methodology."""
    return simulation_engine.get_full_provenance()

@app.post("/api/v1/simulation/run", response_model=SimulationResponse)
def run_simulation(req: SimulationRequest):
    """
    Evaluates a candidate landing site using the verified LOLA DEM and JPL Horizons ephemeris.
    Synthetic Demo fabrication is disabled for scientific integrity.
    """
    try:
        result = simulation_engine.run(
            site_id=req.site_id,
            lat=req.lat,
            lon=req.lon,
            start_time_iso=req.start_time,
            mission_duration_days=req.mission_duration_days,
            timestep_hours=req.timestep_hours,
            antenna_height_m=req.antenna_height_m,
            los_margin_deg=req.los_margin_deg,
            demo_mode=req.demo_mode
        )
        return result
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Simulation execution error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
