"""
Test suite for Lunar Landing Site Navigator FastAPI backend v1.5.
Validates input constraints, timezone handling, coordinate checking,
status endpoints, terrain_aware execution with bundled NASA LOLA DEM
(LDEM_80S_80MPP_ADJ.TIF), engine-pending behavior when coverage is absent,
scientific integrity policy (synthetic Demo disabled), and landing risk assessment.
"""

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

BASE_REQ = {
    "site_id": "shackleton",
    "lat": -89.9,
    "lon": 0.0,
    "start_time": "2026-11-14T12:00:00Z",
    "mission_duration_days": 14,
    "timestep_hours": 4,
    "antenna_height_m": 8.0,
    "los_margin_deg": 0.25,
}


# =========================================================================
# 1. Status & Sites Endpoints
# =========================================================================

def test_service_status():
    res = client.get("/api/v1/status")
    assert res.status_code == 200
    data = res.json()
    assert data["system_status"] == "online"
    assert data["real_calculation_engine"]["status"] == "terrain_engine_ready"
    assert data["real_calculation_engine"]["lola_dem_ingested"] is True
    assert data["demo_mode_available"] is False


def test_list_candidate_sites():
    res = client.get("/api/v1/sites")
    assert res.status_code == 200
    sites = res.json()
    assert len(sites) >= 5
    ids = [s["id"] for s in sites]
    assert "shackleton" in ids
    assert "malapert" in ids
    assert all(s.get("is_illustrative") is True for s in sites)


def test_reference_catalog_contains_real_archive_records_and_disclosures():
    res = client.get("/api/v1/reference/landing-sites")
    assert res.status_code == 200
    catalog = res.json()
    assert catalog["count"] == 130
    assert len(catalog["features"]) == 130
    first = catalog["features"][0]
    assert first["geometry"]["type"] == "Point"
    assert len(first["geometry"]["coordinates"]) == 2
    assert "SunDays26" in first["properties"]
    assert catalog["illumination_raster_products"]
    assert any("not an elevation DEM" in note for note in catalog["source"]["limitations"])


def test_reference_catalog_v2_exposes_archive_summaries_and_scientific_cautions():
    res = client.get("/api/v1/reference/catalog-v2")
    assert res.status_code == 200
    catalog = res.json()
    assert catalog["version"] == "2.0"
    assert catalog["counts"] == {"rasters": 336, "areas": 21, "psr_polygons": 141}
    assert len(catalog["raster_products"]) == 336
    assert len(catalog["areas"]) == 21
    assert len(catalog["psr_polygons"]) == 141
    assert {product["year"] for product in catalog["raster_products"]} == set(range(2025, 2033))
    assert catalog["areas"]["PeakNearShackleton"]["series"]["sun_only"]["mean_days_all_years"] == 7.663
    assert catalog["areas"]["MalapertMassif"]["series"]["sun_plus_earth"]["mean_days_all_years"] == 7.915
    assert catalog["areas"]["Haworth"]["psr_polygons_in_extent"] == 0
    assert "NOT verified" in catalog["provenance_warning"]
    assert catalog["sun_plus_earth_vs_sun_only"]["mean_fraction_pixels_where_sun_plus_earth_exceeds_sun_only"] == 0.0954


# =========================================================================
# 2. Input Validation
# =========================================================================

def test_validation_invalid_site():
    res = client.post("/api/v1/simulation/run", json={**BASE_REQ, "site_id": "nonexistent"})
    assert res.status_code == 404


def test_validation_lat_out_of_range():
    res = client.post("/api/v1/simulation/run", json={**BASE_REQ, "lat": -50.0})
    assert res.status_code == 422


def test_validation_invalid_start_time():
    res = client.post("/api/v1/simulation/run", json={**BASE_REQ, "start_time": "not-a-date"})
    assert res.status_code == 422


def test_validation_naive_timestamp_rejected():
    """A timestamp without timezone info must be rejected."""
    res = client.post("/api/v1/simulation/run", json={
        **BASE_REQ, "start_time": "2026-11-14T12:00:00"
    })
    assert res.status_code == 422


def test_validation_duration_bounds():
    """Duration must be 1-60."""
    res = client.post("/api/v1/simulation/run", json={**BASE_REQ, "mission_duration_days": 0})
    assert res.status_code == 422
    res = client.post("/api/v1/simulation/run", json={**BASE_REQ, "mission_duration_days": 61})
    assert res.status_code == 422


# =========================================================================
# 3. Timezone Handling
# =========================================================================

def test_timezone_utc_z_suffix():
    """A timestamp with 'Z' suffix is interpreted as UTC."""
    res = client.post("/api/v1/simulation/run", json={
        **BASE_REQ,
        "start_time": "2026-11-14T12:00:00Z",
        "demo_mode": False,
        "mission_duration_days": 1,
        "timestep_hours": 24,
    })
    assert res.status_code == 200
    data = res.json()
    assert data["inputs_used"]["start_time_utc"] == "2026-11-14T12:00:00+00:00"
    assert "12:00:00" in data["timeline"][0]["timestamp"]


def test_timezone_positive_offset():
    """A timestamp with +05:00 offset is correctly converted to UTC."""
    res = client.post("/api/v1/simulation/run", json={
        **BASE_REQ,
        "start_time": "2026-11-14T17:00:00+05:00",
        "demo_mode": False,
        "mission_duration_days": 1,
        "timestep_hours": 24,
    })
    assert res.status_code == 200
    data = res.json()
    assert data["inputs_used"]["start_time_utc"] == "2026-11-14T12:00:00+00:00"


def test_timezone_negative_offset():
    """A timestamp with -03:00 offset is correctly converted to UTC."""
    res = client.post("/api/v1/simulation/run", json={
        **BASE_REQ,
        "start_time": "2026-11-14T09:00:00-03:00",
        "demo_mode": False,
        "mission_duration_days": 1,
        "timestep_hours": 24,
    })
    assert res.status_code == 200
    data = res.json()
    assert data["inputs_used"]["start_time_utc"] == "2026-11-14T12:00:00+00:00"


# =========================================================================
# 4. Terrain-Aware Execution & Engine-Pending (No Fabrication)
# =========================================================================

def test_engine_pending_no_fabrication():
    """Requests outside recorded ephemeris coverage must return engine_pending with zero fabricated KPIs."""
    res = client.post("/api/v1/simulation/run", json={
        **BASE_REQ,
        "start_time": "2026-12-01T00:00:00Z",
        "demo_mode": False,
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "engine_pending"
    assert data["data_source"] == "none"
    assert data["is_demo"] is False
    assert data["kpis"] is None
    assert data["timeline"] == []
    assert data["total_time_steps"] == 0


def test_demo_timeline_count_matches_inputs():
    """Covered 48h window at 6-hour steps returns only real Horizons steps (8 steps for 2 days) and never fabricates."""
    res = client.post("/api/v1/simulation/run", json={
        **BASE_REQ,
        "start_time": "2026-11-14T12:00:00Z",
        "mission_duration_days": 2,
        "timestep_hours": 6,
        "demo_mode": True,
    })
    data = res.json()
    assert data["status"] == "terrain_aware"
    assert data["is_demo"] is False
    assert data["total_time_steps"] == 8
    assert len(data["timeline"]) == 8
    assert data["timeline"][0]["elapsed_hours"] == 0
    assert data["timeline"][1]["elapsed_hours"] == 6


def test_demo_timeline_3_days_12h_steps():
    """Even when demo_mode=True is requested on an uncovered date, no synthetic timeline is fabricated."""
    res = client.post("/api/v1/simulation/run", json={
        **BASE_REQ,
        "start_time": "2026-12-01T00:00:00Z",
        "mission_duration_days": 3,
        "timestep_hours": 12,
        "demo_mode": True,
    })
    data = res.json()
    assert data["status"] == "engine_pending"
    assert data["is_demo"] is False
    assert data["timeline"] == []


def test_demo_antenna_height_impacts_dte():
    """Higher antenna mast lowers the ray-traced local terrain horizon angle."""
    res_low = client.post("/api/v1/simulation/run", json={
        **BASE_REQ, "antenna_height_m": 0.0, "demo_mode": False, "mission_duration_days": 2, "timestep_hours": 6
    })
    res_high = client.post("/api/v1/simulation/run", json={
        **BASE_REQ, "antenna_height_m": 18.0, "demo_mode": False, "mission_duration_days": 2, "timestep_hours": 6
    })
    assert res_high.json()["terrain_info"]["horizon_mean_deg"] < res_low.json()["terrain_info"]["horizon_mean_deg"]


def test_demo_los_margin_impacts_illumination():
    """In real physics, LOS margin tightens Earth clearance without corrupting solar illumination."""
    res_low = client.post("/api/v1/simulation/run", json={
        **BASE_REQ, "los_margin_deg": 0.0, "demo_mode": False, "mission_duration_days": 2, "timestep_hours": 6
    })
    res_high = client.post("/api/v1/simulation/run", json={
        **BASE_REQ, "los_margin_deg": 2.0, "demo_mode": False, "mission_duration_days": 2, "timestep_hours": 6
    })
    assert res_low.json()["kpis"]["avg_illumination_pct"] == res_high.json()["kpis"]["avg_illumination_pct"]


# =========================================================================
# 6. Coordinate Mismatch Warning
# =========================================================================

def test_coordinate_mismatch_warning():
    """Submitting coordinates that differ from registered site produces a warning."""
    res = client.post("/api/v1/simulation/run", json={
        **BASE_REQ,
        "lat": -89.5,
        "lon": 1.0,
        "demo_mode": False,
    })
    data = res.json()
    assert data["coordinate_mismatch"] is not None
    assert "differ" in data["coordinate_mismatch"].lower()


def test_matching_coordinates_no_warning():
    """Matching coordinates produce no mismatch warning."""
    res = client.post("/api/v1/simulation/run", json={
        **BASE_REQ, "lat": -89.9, "lon": 0.0, "demo_mode": False,
    })
    data = res.json()
    assert data["coordinate_mismatch"] is None


# =========================================================================
# 7. Response Structure
# =========================================================================

def test_response_contains_all_required_fields():
    """Every response must include status, data_source, inputs_used, generated_at, units, and landing_risk_assessment."""
    res = client.post("/api/v1/simulation/run", json={**BASE_REQ, "demo_mode": False})
    data = res.json()
    for field in ["status", "status_message", "data_source", "is_demo",
                  "inputs_used", "units", "timeline", "total_time_steps",
                  "landing_risk_assessment", "generated_at"]:
        assert field in data, f"Missing field: {field}"
    for key in ["site_id", "start_time_utc", "mission_duration_days", "timestep_hours",
                "antenna_height_m", "los_margin_deg", "demo_mode"]:
        assert key in data["inputs_used"], f"Missing input echo: {key}"


def test_demo_not_returned_when_not_requested():
    """When covered by bundled NASA LOLA DEM and JPL Horizons, simulation returns real terrain_aware data (is_demo=False)."""
    res = client.post("/api/v1/simulation/run", json={**BASE_REQ, "mission_duration_days": 2, "timestep_hours": 6, "demo_mode": False})
    data = res.json()
    assert data["status"] == "terrain_aware"
    assert data["data_source"] == "real_engine"
    assert data["is_demo"] is False
    assert data["kpis"] is not None
    assert len(data["timeline"]) == 8


def test_api_exposes_ephemeris_check_field():
    """The response model must not drop the real-NASA-data block."""
    res = client.post("/api/v1/simulation/run", json={**BASE_REQ, "demo_mode": False, "mission_duration_days": 2,
                                                       "timestep_hours": 6})
    assert res.status_code == 200
    eph = res.json()["ephemeris_check"]
    assert eph["source"] == "jpl_horizons_recorded_fixture"
    assert eph["coverage"]["steps_with_real_ephemeris"] == 8


def test_recorded_multi_site_horizons_fixture_is_discovered():
    from services.ephemeris_provider import EphemerisProvider
    provider = EphemerisProvider(live_enabled=False)
    result = provider._fixture_series(-85.0, 0.0)
    assert result is not None
    sun, earth, metadata = result
    assert len(sun) >= 20 and len(earth) >= 20
    assert metadata["recorded_metadata"]["site"] == "Malapert Massif"
    assert provider._fixture_series(-70.0, 0.0) is None
