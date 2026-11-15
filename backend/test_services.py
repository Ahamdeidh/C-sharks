"""
Unit Test Suite for Modular Backend Services
=============================================
Tests:
- JPL Horizons Service (query formation, caching, CSV parsing, error handling)
- NAIF SPICE Frame Transformations (ENU topocentric basis, mathematical reference cases)
- DEM Service (Polar stereographic projection, synthetic benchmark grid, metadata)
- Illumination & LOS Service (lunar curvature, antenna height, finite disc penumbra, DTE margin, horizon crossings)
- Simulation Engine (coordinate precedence, provenance generation)
"""

import math
from datetime import datetime, timezone
import pytest

from services.horizons_service import HorizonsService, HorizonsServiceError, HorizonsTimeoutError
from services.spice_service import SpiceKernelStatus, LocalFrameTransform
from services.dem_service import DemService, LUNAR_RADIUS_M
from services.illumination_service import (
    IlluminationService,
    SOLAR_ANGULAR_RADIUS_DEG,
    EARTH_ANGULAR_RADIUS_DEG
)
from services.simulation_engine import SimulationEngine, PREDEFINED_SITES

# =========================================================================
# 1. JPL Horizons Service Tests
# =========================================================================

def test_horizons_query_params_building():
    svc = HorizonsService(enable_network=False)
    params = svc.build_query_params(
        target_id="10",
        lat=-89.9,
        lon=-2.9,
        elevation_km=4.2,
        start_time_utc=datetime(2026, 11, 14, 12, 0, tzinfo=timezone.utc),
        stop_time_utc=datetime(2026, 11, 14, 18, 0, tzinfo=timezone.utc),
        step_hours=6
    )

    assert params["COMMAND"] == "'10'"
    assert params["CENTER"] == "'coord@301'"
    assert params["QUANTITIES"] == "'4'"
    assert params["EPHEM_TYPE"] == "OBSERVER"
    assert params["REF_SYSTEM"] == "'ICRF'"
    assert "357.1000,-89.9000,4.200" in params["SITE_COORD"]

def test_horizons_csv_parsing_real_with_flags():
    """Tests parsing real Horizons lines with solar and lunar presence flags ('*', 'm', ' ')."""
    svc = HorizonsService(enable_network=False)
    real_horizons_output = """
    *******************************************************************************
    Date__(UT)__HR:MN, , ,Azi_(a-app), Elev_(a-app),
    *************************************************
    $$SOE
     2026-Nov-14 12:00,*, , 120.525991,     1.505818,
     2026-Nov-14 18:00, , , 117.479693,     -1.510370,
     2026-Nov-15 00:00,*,m, 114.433749,     1.514992,
    $$EOE
    *******************************************************************************
    """
    samples = svc.parse_horizons_csv(real_horizons_output)
    assert len(samples) == 3
    assert samples[0]["time_str"] == "2026-Nov-14 12:00"
    assert pytest.approx(samples[0]["azimuth_deg"], 0.0001) == 120.525991
    assert pytest.approx(samples[0]["elevation_deg"], 0.0001) == 1.505818
    assert pytest.approx(samples[1]["elevation_deg"], 0.0001) == -1.510370
    assert pytest.approx(samples[2]["azimuth_deg"], 0.0001) == 114.433749

def test_horizons_load_recorded_fixture():
    """Tests loading the real recorded JPL Horizons fixture from disk."""
    svc = HorizonsService(enable_network=False)
    sun_samples, sun_meta = svc.load_recorded_fixture(target_id="10")
    assert len(sun_samples) > 0
    assert sun_meta["is_fixture"] is True
    assert sun_meta["target_id"] == "10"
    assert "azimuth_deg" in sun_samples[0]
    assert "elevation_deg" in sun_samples[0]

    earth_samples, earth_meta = svc.load_recorded_fixture(target_id="399")
    assert len(earth_samples) > 0
    assert earth_meta["target_id"] == "399"

def test_horizons_csv_parsing_valid():
    svc = HorizonsService(enable_network=False)
    mock_horizons_output = """
    *******************************************************************************
    $$SOE
    2026-Nov-14 12:00, 184.2341,  1.4215,
    2026-Nov-14 18:00, 190.5120,  1.3890,
    $$EOE
    *******************************************************************************
    """
    samples = svc.parse_horizons_csv(mock_horizons_output)
    assert len(samples) == 2
    assert samples[0]["azimuth_deg"] == 184.2341
    assert samples[0]["elevation_deg"] == 1.4215
    assert samples[1]["azimuth_deg"] == 190.5120
    assert samples[1]["elevation_deg"] == 1.3890

def test_horizons_csv_parsing_missing_block():
    svc = HorizonsService(enable_network=False)
    with pytest.raises(HorizonsServiceError, match="does not contain expected"):
        svc.parse_horizons_csv("No ephemeris block here")

def test_horizons_network_disabled_guard():
    svc = HorizonsService(enable_network=False)
    with pytest.raises(HorizonsServiceError, match="disabled by configuration"):
        svc.query_observer_ephemeris(
            target_id="10",
            lat=-89.9,
            lon=0.0,
            elevation_km=0.0,
            start_time_utc=datetime.now(timezone.utc),
            stop_time_utc=datetime.now(timezone.utc),
            step_hours=4
        )


# =========================================================================
# 2. SPICE Reference Frame Transformation Tests
# =========================================================================

def test_spice_kernel_inventory():
    status = SpiceKernelStatus()
    coverage = status.evaluate_kernel_coverage()
    assert "kernel_inventory" in coverage
    assert len(coverage["kernel_inventory"]) == 4
    names = [k["name"] for k in coverage["kernel_inventory"]]
    assert "naif0012.tls" in names
    assert "de430.bsp" in names

def test_local_frame_transform_south_pole():
    """
    Observer at Lunar South Pole (-90° Lat, 0° Lon):
    - Up (Zenith) is along -Z
    - North points toward Prime Meridian (+X)
    - East points toward 90°E (+Y)
    """
    u_E, u_N, u_U = LocalFrameTransform.body_fixed_to_topocentric_basis(-90.0, 0.0)

    # Check unit vectors
    assert u_U == (0.0, 0.0, -1.0)
    assert u_N == (1.0, 0.0, 0.0)
    assert u_E == (0.0, 1.0, 0.0)

    # Target along +X (Prime Meridian) -> Elevation 0°, Azimuth 0° (North)
    az, el = LocalFrameTransform.vector_to_azimuth_elevation((1000.0, 0.0, 0.0), -90.0, 0.0)
    assert math.isclose(az, 0.0, abs_tol=1e-4)
    assert math.isclose(el, 0.0, abs_tol=1e-4)

    # Target along +Y (90°E) -> Elevation 0°, Azimuth 90° (East)
    az_east, el_east = LocalFrameTransform.vector_to_azimuth_elevation((0.0, 1000.0, 0.0), -90.0, 0.0)
    assert math.isclose(az_east, 90.0, abs_tol=1e-4)
    assert math.isclose(el_east, 0.0, abs_tol=1e-4)

    # Target straight overhead (Zenith, -Z) -> Elevation +90°
    az_zenith, el_zenith = LocalFrameTransform.vector_to_azimuth_elevation((0.0, 0.0, -1000.0), -90.0, 0.0)
    assert math.isclose(el_zenith, 90.0, abs_tol=1e-4)

def test_local_frame_transform_equator():
    """
    Observer at Equator (0° Lat, 0° Lon):
    - Up (Zenith) is along +X
    - North is along +Z
    - East is along +Y
    """
    u_E, u_N, u_U = LocalFrameTransform.body_fixed_to_topocentric_basis(0.0, 0.0)
    assert math.isclose(u_U[0], 1.0, abs_tol=1e-5)
    assert math.isclose(u_N[2], 1.0, abs_tol=1e-5)
    assert math.isclose(u_E[1], 1.0, abs_tol=1e-5)


# =========================================================================
# 3. DEM Service Tests
# =========================================================================

def test_polar_stereographic_roundtrip():
    dem = DemService()
    test_lat, test_lon = -87.5, 45.0
    x, y = dem.latlon_to_polar_stereographic(test_lat, test_lon)
    lat_rt, lon_rt = dem.polar_stereographic_to_latlon(x, y)

    assert math.isclose(test_lat, lat_rt, abs_tol=1e-4)
    assert math.isclose(test_lon, lon_rt, abs_tol=1e-4)

def test_synthetic_benchmark_dem_creation():
    raster, meta = DemService.create_synthetic_benchmark_dem(
        grid_size=51,
        resolution_m=100.0,
        center_elev_m=0.0,
        obstacle_distance_m=500.0,
        obstacle_height_m=150.0,
        obstacle_azimuth_deg=0.0  # North
    )

    assert raster.shape == (51, 51)
    assert meta.is_synthetic is True
    assert meta.resolution_m_per_px == 100.0
    assert meta.nodata_value == -32768.0

    # Center is at (25, 25) with elevation ~0m
    center_idx = 25
    assert math.isclose(raster[center_idx, center_idx], 0.0, abs_tol=1e-2)

    # Obstacle is 500m North (5 cells up in row direction) -> row 20, col 25
    assert raster[20, 25] > 100.0


# =========================================================================
# 4. Illumination & Line-of-Sight Geometry Tests
# =========================================================================

def test_lunar_curvature_drop():
    # Distance 10 km (10,000 m). Drop should be r^2 / (2 * R_Moon)
    r = 10000.0
    expected_drop = (r * r) / (2.0 * LUNAR_RADIUS_M)  # 100,000,000 / 3,474,800 ≈ 28.77 meters
    assert 28.0 < expected_drop < 29.0

    angle_zero_elev = IlluminationService.compute_apparent_terrain_elevation_angle(
        distance_m=r,
        terrain_elevation_m=0.0,
        observer_ground_elevation_m=0.0,
        antenna_height_m=0.0
    )
    # Curvature causes flat terrain at 10km to dip below 0° elevation
    assert angle_zero_elev < 0.0

def test_antenna_height_reduces_horizon_elevation():
    # Terrain obstacle 1000m away, 50m high
    r = 1000.0
    elev = 50.0

    angle_surface = IlluminationService.compute_apparent_terrain_elevation_angle(
        distance_m=r,
        terrain_elevation_m=elev,
        observer_ground_elevation_m=0.0,
        antenna_height_m=0.0
    )

    angle_mast_10m = IlluminationService.compute_apparent_terrain_elevation_angle(
        distance_m=r,
        terrain_elevation_m=elev,
        observer_ground_elevation_m=0.0,
        antenna_height_m=10.0
    )

    # Raising antenna mast must strictly lower apparent elevation of the obstacle
    assert angle_mast_10m < angle_surface

def test_solar_illumination_finite_disc():
    horizon_el = 2.0  # Horizon at 2.0°

    # Case 1: Sun well above horizon (> 2.0° + 0.26°) -> Full sun
    res_high = IlluminationService.evaluate_solar_illumination(sun_elevation_deg=3.0, horizon_elevation_deg=horizon_el)
    assert res_high["state"] == "full_sun"
    assert res_high["percentage"] == 100.0

    # Case 2: Sun below horizon (< 2.0° - 0.26°) -> Total shadow
    res_low = IlluminationService.evaluate_solar_illumination(sun_elevation_deg=1.0, horizon_elevation_deg=horizon_el)
    assert res_low["state"] == "shadow"
    assert res_low["percentage"] == 0.0

    # Case 3: Sun center exactly on horizon (2.0°) -> Partial penumbra (50%)
    res_mid = IlluminationService.evaluate_solar_illumination(sun_elevation_deg=2.0, horizon_elevation_deg=horizon_el)
    assert res_mid["state"] == "penumbra"
    assert math.isclose(res_mid["percentage"], 50.0, abs_tol=1.0)

def test_dte_communication_with_margin():
    horizon_el = 1.0
    margin = 0.5  # Effective threshold = 1.5°

    # Earth center at 3.0° -> Well above threshold + Earth radius (~0.9°)
    res_clear = IlluminationService.evaluate_dte_communication(
        earth_elevation_deg=3.0,
        horizon_elevation_deg=horizon_el,
        los_margin_deg=margin
    )
    assert res_clear["is_connected"] is True
    assert res_clear["state"] == "clear_los"

    # Earth center at 0.5° -> Below threshold - Earth radius
    res_blocked = IlluminationService.evaluate_dte_communication(
        earth_elevation_deg=0.5,
        horizon_elevation_deg=horizon_el,
        los_margin_deg=margin
    )
    assert res_blocked["is_connected"] is False
    assert res_blocked["state"] == "occluded"

def test_horizon_crossing_detection():
    elev_series = [1.0, 1.5, 2.5, 3.0, 1.8, 0.5]
    horiz_series = [2.0, 2.0, 2.0, 2.0, 2.0, 2.0]
    crossings = IlluminationService.detect_horizon_crossings(elev_series, horiz_series)
    # Crosses between step 1 (1.5) and 2 (2.5), and between step 3 (3.0) and 4 (1.8) or 4 and 5
    assert len(crossings) >= 2


# =========================================================================
# 5. Simulation Engine Orchestrator Tests
# =========================================================================

def test_simulation_engine_coordinate_precedence():
    engine = SimulationEngine()

    # Predefined coordinates matching Shackleton
    site, lat, lon, warn, rule = engine.resolve_site_coordinates("shackleton", -89.9, 0.0)
    assert warn is None
    assert rule == "predefined registered site coordinates"
    assert lat == -89.9

    # Custom coordinates overriding Shackleton
    site, lat, lon, warn, rule = engine.resolve_site_coordinates("shackleton", -89.2, 10.0)
    assert warn is not None
    assert rule == "custom coordinates override predefined site"
    assert lat == -89.2
    assert lon == 10.0

def test_simulation_engine_provenance_structure():
    engine = SimulationEngine()
    prov = engine.get_full_provenance()
    assert "official_sources" in prov
    assert len(prov["official_sources"]) >= 4
    source_names = [s["name"] for s in prov["official_sources"]]
    assert any("Horizons" in name for name in source_names)
    assert any("ODE" in name for name in source_names)
    assert any("SPICE" in name for name in source_names)
    assert any("Moon Trek" in name for name in source_names)

def test_dem_raytracing_with_obstacle():
    """Verifies that DemService.compute_horizon_profile correctly detects obstacle elevation."""
    grid, meta = DemService.create_synthetic_benchmark_dem(
        grid_size=51,
        resolution_m=100.0,
        obstacle_distance_m=500.0,
        obstacle_height_m=150.0,
        obstacle_azimuth_deg=0.0
    )
    # Observer at center (25, 25)
    prof = DemService.compute_horizon_profile(grid, 25, 25, resolution_m=100.0, antenna_height_m=0.0, num_azimuths=36)
    # Along 0 deg (North), obstacle elevation should be ~16.7 deg
    assert prof["horizon_angles"][0.0] > 15.0
    # Along 90 deg (East, flat terrain), horizon should be ~0 or slightly negative due to curvature
    assert prof["horizon_angles"][90.0] < 1.0

def test_dem_antenna_height_improves_horizon_clearance():
    """Verifies that increasing antenna mast height lowers the apparent horizon obstruction angle."""
    grid, meta = DemService.create_synthetic_benchmark_dem(
        grid_size=51,
        resolution_m=100.0,
        obstacle_distance_m=500.0,
        obstacle_height_m=150.0,
        obstacle_azimuth_deg=0.0
    )
    prof_0m = DemService.compute_horizon_profile(grid, 25, 25, resolution_m=100.0, antenna_height_m=0.0, num_azimuths=36)
    prof_20m = DemService.compute_horizon_profile(grid, 25, 25, resolution_m=100.0, antenna_height_m=20.0, num_azimuths=36)

    # 20m mast should decrease the apparent elevation angle of the obstacle
    assert prof_20m["horizon_angles"][0.0] < prof_0m["horizon_angles"][0.0]
    angle_drop = prof_0m["horizon_angles"][0.0] - prof_20m["horizon_angles"][0.0]
    assert angle_drop > 1.5  # At least 1.5 degrees clearance improvement

def test_simulation_engine_tradeoffs_and_hazards_disclaimer():
    """Verifies that candidate site trade-offs and landing hazard boundaries are provided."""
    engine = SimulationEngine()
    res = engine.run(
        site_id="shackleton",
        lat=-89.9,
        lon=0.0,
        start_time_iso="2026-11-14T12:00:00Z",
        mission_duration_days=14,
        timestep_hours=4,
        antenna_height_m=6.0,
        los_margin_deg=0.25,
        demo_mode=True
    )
    kpis = res["kpis"]
    assert "tradeoffs" in kpis
    assert "advantages" in kpis["tradeoffs"]
    assert "downsides" in kpis["tradeoffs"]
    assert "landing_hazards_disclaimer" in kpis
    assert "longest_continuous_darkness_hours" in kpis
    assert "longest_earth_blackout_hours" in kpis
    assert "geometric_dte_visibility_pct" in kpis


# =========================================================================
# 9. Real NASA Horizons angles in simulation responses (ephemeris_check)
# =========================================================================

from datetime import timedelta
from services.ephemeris_provider import EphemerisProvider
from services.horizons_service import parse_horizons_time

SHACKLETON = next(s for s in PREDEFINED_SITES if s["id"] == "shackleton")
FIXTURE_START = datetime(2026, 11, 14, 12, 0, tzinfo=timezone.utc)


def _offline_provider():
    return EphemerisProvider(live_enabled=False)


def test_parse_horizons_time_is_utc_and_locale_independent():
    dt = parse_horizons_time(" 2026-Nov-14 18:00")
    assert dt == datetime(2026, 11, 14, 18, 0, tzinfo=timezone.utc)


def test_load_recorded_fixture_accepts_explicit_path():
    """Regression: an explicit fixture_path used to raise UnboundLocalError (local `import os`)."""
    import os
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "fixtures",
                        "horizons_sun_earth_sample.json")
    samples, meta = HorizonsService().load_recorded_fixture(path, target_id="10")
    assert len(samples) == 9 and meta["is_fixture"] is True


def test_ephemeris_exact_fixture_values_at_recorded_times():
    res = _offline_provider().get_ephemeris_check(
        lat=-89.9, lon=0.0, elevation_m=4200.0, start_utc=FIXTURE_START, step_hours=6, total_steps=9)
    assert res["source"] == "jpl_horizons_recorded_fixture"
    first, last = res["samples"][0], res["samples"][-1]
    # values copied from the recorded NASA Horizons output
    assert first["sun_elevation_deg"] == pytest.approx(1.506, abs=1e-3)
    assert first["sun_azimuth_deg"] == pytest.approx(120.526, abs=1e-3)
    assert first["earth_elevation_deg"] == pytest.approx(-4.022, abs=1e-3)
    assert last["earth_elevation_deg"] == pytest.approx(-1.550, abs=1e-3)
    assert res["coverage"]["steps_with_real_ephemeris"] == 9


def test_ephemeris_interpolates_between_recorded_samples():
    res = _offline_provider().get_ephemeris_check(
        lat=-89.9, lon=0.0, elevation_m=4200.0, start_utc=FIXTURE_START, step_hours=3, total_steps=2)
    mid = res["samples"][1]  # 15:00 UTC, halfway between 12:00 and 18:00 samples
    assert mid["sun_elevation_deg"] == pytest.approx((1.505816 + 1.510369) / 2, abs=1e-3)
    assert mid["earth_elevation_deg"] == pytest.approx((-4.022090 + -3.742737) / 2, abs=1e-3)


def test_ephemeris_never_extrapolates_outside_recorded_window():
    res = _offline_provider().get_ephemeris_check(
        lat=-89.9, lon=0.0, elevation_m=4200.0, start_utc=FIXTURE_START, step_hours=12, total_steps=10)
    # only 12:00 Nov-14 ... 12:00 Nov-16 (5 steps) are covered; steps 6-10 are omitted
    assert res["coverage"]["steps_requested"] == 10
    assert res["coverage"]["steps_with_real_ephemeris"] == 5


def test_ephemeris_none_for_other_sites_or_dates():
    provider = _offline_provider()
    assert provider.get_ephemeris_check(
        lat=-85.9, lon=-2.9, elevation_m=5000.0, start_utc=FIXTURE_START, step_hours=6, total_steps=9) is None
    later = FIXTURE_START + timedelta(days=30)
    assert provider.get_ephemeris_check(
        lat=-89.9, lon=0.0, elevation_m=4200.0, start_utc=later, step_hours=6, total_steps=9) is None


def test_ephemeris_live_disabled_by_default():
    import os
    os.environ.pop("ENABLE_LIVE_HORIZONS", None)
    assert EphemerisProvider().live_enabled is False


def test_ephemeris_live_failure_falls_back_to_fixture():
    class FailingHorizons(HorizonsService):
        def query_observer_ephemeris(self, *a, **k):
            raise HorizonsServiceError("network down")

    provider = EphemerisProvider(horizons=FailingHorizons(), live_enabled=True)
    res = provider.get_ephemeris_check(
        lat=-89.9, lon=0.0, elevation_m=4200.0, start_utc=FIXTURE_START, step_hours=6, total_steps=3)
    assert res["source"] == "jpl_horizons_recorded_fixture"
    assert "network down" in res["live_error"]


def test_ephemeris_live_success_is_labelled_live():
    class StubHorizons(HorizonsService):
        def query_observer_ephemeris(self, target_id, **k):
            el = 2.0 if target_id == "10" else 5.0
            return [{"time_str": "2030-Jan-01 00:00", "azimuth_deg": 10.0, "elevation_deg": el},
                    {"time_str": "2030-Jan-01 06:00", "azimuth_deg": 20.0, "elevation_deg": el}]

    provider = EphemerisProvider(horizons=StubHorizons(), live_enabled=True)
    res = provider.get_ephemeris_check(
        lat=-85.9, lon=-2.9, elevation_m=5000.0,
        start_utc=datetime(2030, 1, 1, tzinfo=timezone.utc), step_hours=6, total_steps=2)
    assert res["source"] == "jpl_horizons_live"
    assert res["summary"]["earth_above_local_horizontal_pct"] == 100.0


def test_engine_demo_attaches_real_ephemeris_for_shackleton():
    engine = SimulationEngine()
    res = engine.run("shackleton", -89.9, 0.0, "2026-11-14T12:00:00Z", 2, 6, 8.0, 0.25, demo_mode=True)
    assert res["status"] == "terrain_aware"
    assert res["is_demo"] is False
    assert res["ephemeris_check"]["source"] == "jpl_horizons_recorded_fixture"
    assert "real JPL Horizons angles" in res["status_message"]


def test_engine_demo_without_real_coverage_says_so():
    engine = SimulationEngine()
    res = engine.run("malapert", -85.9, -2.9, "2026-11-14T12:00:00Z", 2, 6, 8.0, 0.25, demo_mode=True)
    assert res["status"] == "engine_pending"
    assert res["is_demo"] is False
    assert res["ephemeris_check"] is None
    assert "outside the recorded JPL Horizons fixture" in res["status_message"]


def test_engine_pending_includes_real_ephemeris_without_fabricating_kpis(tmp_path):
    engine = SimulationEngine(dem_dir=str(tmp_path))
    res = engine.run("shackleton", -89.9, 0.0, "2026-11-14T12:00:00Z", 2, 6, 8.0, 0.25, demo_mode=False)
    assert res["status"] == "engine_pending"
    assert res["kpis"] is None and res["timeline"] == []
    assert res["ephemeris_check"]["coverage"]["steps_with_real_ephemeris"] == 8


def test_longrange_clps_horizons_fixture_has_exact_coverage_and_site_metadata():
    from datetime import datetime, timezone
    provider = EphemerisProvider(live_enabled=False)
    result = provider.get_ephemeris_check(-89.63, 132.32, 0.0, datetime(2026, 11, 15, tzinfo=timezone.utc), 6, 5)
    assert result is not None
    assert result["coverage"]["coverage_complete"] is True
    assert result["coverage"]["steps_with_real_ephemeris"] == 5
    assert result["fixture"]["site"] == "CLPS Shackleton Connecting Ridge"
    assert result["fixture"]["coordinates"]["elevation_km"] == 0.0
    assert "EOP" in result["fixture"]["source_caveat"]


def test_longrange_horizons_does_not_extrapolate_beyond_2028():
    from datetime import datetime, timezone
    provider = EphemerisProvider(live_enabled=False)
    result = provider.get_ephemeris_check(-89.63, 132.32, 0.0, datetime(2029, 1, 1, tzinfo=timezone.utc), 1, 1)
    assert result is None


def test_longrange_horizons_raw_ephemeris_does_not_create_fused_kpis_at_altitude_mismatch():
    engine = SimulationEngine()
    result = engine.run("connecting-ridge", -89.63, 132.32, "2026-11-15T00:00:00Z", 1, 6, 6.0, 0.25, False)
    assert result["ephemeris_check"] is not None
    assert result["ephemeris_check"]["coverage"]["coverage_complete"] is True
    assert result["status"] == "engine_pending"
    assert result["kpis"] is None and result["timeline"] == []
    assert result["reference_kpis"] is None
    assert "raw ephemeris only" in result["status_message"]
    assert "ephemeris_altitude_mismatch_warning" in result["inputs_used"]
