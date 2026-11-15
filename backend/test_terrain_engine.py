import json
import math

import numpy as np
import pytest
from fastapi.testclient import TestClient

try:
    import tifffile
    def _save_tif(path: str, raster: np.ndarray) -> None:
        tifffile.imwrite(path, raster)
except ImportError:
    from PIL import Image
    def _save_tif(path: str, raster: np.ndarray) -> None:
        if raster.dtype == np.uint8:
            Image.fromarray(raster, mode="L").save(path, format="TIFF")
        else:
            Image.fromarray(np.asarray(raster, dtype=np.float32), mode="F").save(path, format="TIFF")

from main import app
from services.dem_service import DemService
from services.simulation_engine import SimulationEngine
from services.terrain_engine import (
    compute_bidirectional_pad_metrics,
    compute_reference_kpis,
    flat_horizon_dip_deg,
    horizon_function,
    load_verified_dem,
    true_to_grid_azimuth,
    verify_dem_geodesy_and_control_points,
    VerifiedDem,
)
from services.verification_suite import run_benchmarks

client = TestClient(app)
RES = 100.0


def _meta(lat, lon, size, synthetic=True):
    x, y = DemService.latlon_to_polar_stereographic(lat, lon)
    c = size // 2
    return {
        "product_id": "TEST_DEM", "resolution_m_per_px": RES,
        "pole_row": c + y / RES, "pole_col": c - x / RES,
        "elevation_units": "meters", "vertical_datum": "1737.4 km sphere",
        "projection": "polar_stereographic_south_lon0", "source_url": "test://synthetic",
        "nodata_value": -32768.0, "is_synthetic": synthetic,
    }


def _write_dem(tmp_path, lat, lon, raster, synthetic=True, meta_override=None, with_meta=True):
    _save_tif(str(tmp_path / "dem.tif"), raster)
    if with_meta:
        meta = {**_meta(lat, lon, raster.shape[0], synthetic), **(meta_override or {})}
        (tmp_path / "dem.meta.json").write_text(json.dumps(meta))
    return str(tmp_path)


def test_all_analytic_benchmarks_pass():
    result = run_benchmarks()
    failed = [r["id"] for r in result["results"] if not r["passed"]]
    assert result["all_passed"], failed
    assert result["total"] >= 16


def test_benchmarks_endpoint():
    body = client.get("/api/v1/validation/benchmarks").json()
    assert body["all_passed"] is True
    assert body["total"] >= 16


def test_true_north_maps_to_grid_east_at_lon_90_and_pillar_peaks_at_true_north(tmp_path):
    size, lat, lon = 201, -89.95, 90.0
    raster = np.zeros((size, size), dtype=np.float32)
    c = size // 2
    raster[c, c + 10] = 200.0          # grid east of the site == true north when lon = 90
    dem = VerifiedDem(raster, _meta(lat, lon, size), "x.tif")
    H, _ = horizon_function(dem, lat, lon, antenna_height_m=0.0, max_radius_m=2500.0)
    assert true_to_grid_azimuth(0.0, lon) == pytest.approx(90.0)
    assert H(0.0) > 10.0
    assert H(180.0) < 0.0


def test_dem_without_sidecar_is_rejected(tmp_path):
    raster = np.zeros((101, 101), dtype=np.float32)
    path = _write_dem(tmp_path, -89.9, 0.0, raster, with_meta=False)
    dem, report = load_verified_dem(path)
    assert dem is None and "sidecar" in report["candidates"][0]["reason"]


def test_uint8_suitability_raster_is_rejected(tmp_path):
    raster = np.zeros((101, 101), dtype=np.uint8)
    path = _write_dem(tmp_path, -89.9, 0.0, raster)
    dem, report = load_verified_dem(path)
    assert dem is None and "suitability" in report["candidates"][0]["reason"]


def test_incomplete_or_wrong_projection_metadata_rejected(tmp_path):
    raster = np.zeros((101, 101), dtype=np.float32)
    path = _write_dem(tmp_path, -89.9, 0.0, raster, meta_override={"projection": "web_mercator"})
    assert load_verified_dem(path)[0] is None


def test_strict_mode_without_dem_still_pending_but_has_real_reference_kpis(tmp_path):
    engine = SimulationEngine(dem_dir=str(tmp_path))
    res = engine.run("shackleton", -89.9, 0.0, "2026-11-14T12:00:00Z", 2, 6, 6.0, 0.25, False)
    assert res["status"] == "engine_pending"
    assert res["kpis"] is None and res["timeline"] == []
    ref = res["reference_kpis"]
    assert ref["steps_evaluated"] == 8
    assert ref["geometric_dte_visibility_pct"] == 0.0     # real Earth is below the local horizon
    assert ref["avg_illumination_pct"] == 100.0
    assert ref["longest_earth_blackout_hours"] == 48.0
    assert res["validation_report"]["status"] == "partial_real_data"
    assert any(c["id"] == "analytic_benchmarks" and c["status"] == "pass" for c in res["validation_report"]["checks"])


def test_reference_kpis_none_without_ephemeris():
    assert compute_reference_kpis(None, 6.0, 0.25, 6) is None


def test_mast_dip_formula():
    assert flat_horizon_dip_deg(0) == 0.0
    assert flat_horizon_dip_deg(6.0) == pytest.approx(-math.degrees(math.acos(1737400 / (1737400 + 6))), abs=5e-3)


def test_terrain_engine_runs_with_verified_synthetic_dem_and_labels_it(tmp_path):
    size = 201
    raster = np.zeros((size, size), dtype=np.float32)
    path = _write_dem(tmp_path, -89.9, 0.0, raster, synthetic=True)
    engine = SimulationEngine(dem_dir=path)
    res = engine.run("shackleton", -89.9, 0.0, "2026-11-14T12:00:00Z", 2, 6, 6.0, 0.25, False)
    assert res["status"] == "terrain_benchmark"
    assert res["is_demo"] is True and res["data_source"] == "synthetic_terrain_benchmark"
    assert len(res["timeline"]) == 8                      # only real Horizons steps
    assert res["terrain_info"]["is_synthetic_benchmark"] is True
    assert res["validation_report"]["status"] == "terrain_engine_benchmark"
    assert any(c["id"] == "terrain_pipeline" and c["status"] == "warn" for c in res["validation_report"]["checks"])


def test_real_flagged_dem_gets_terrain_aware_status_and_terrain_changes_result(tmp_path):
    size = 201
    flat = np.zeros((size, size), dtype=np.float32)
    ridge = flat.copy()
    ridge[:, :] = np.maximum(ridge, 0)
    ridge[90:111, 105:140] = 400.0   # tall plateau east of the site (site itself stays at 0 m)
    flat_dir = tmp_path / "flat"; flat_dir.mkdir()
    ridge_dir = tmp_path / "ridge"; ridge_dir.mkdir()
    _write_dem(flat_dir, -89.9, 0.0, flat, synthetic=False)
    _write_dem(ridge_dir, -89.9, 0.0, ridge, synthetic=False)
    args = ("shackleton", -89.9, 0.0, "2026-11-14T12:00:00Z", 2, 6, 6.0, 0.25, False)
    a = SimulationEngine(dem_dir=str(flat_dir)).run(*args)
    b = SimulationEngine(dem_dir=str(ridge_dir)).run(*args)
    assert a["status"] == b["status"] == "terrain_aware"
    assert a["is_demo"] is False and a["data_source"] == "real_engine"
    assert b["terrain_info"]["horizon_max_deg"] > a["terrain_info"]["horizon_max_deg"]
    assert b["kpis"]["avg_illumination_pct"] <= a["kpis"]["avg_illumination_pct"]


def test_demo_mode_is_unchanged_when_dem_present(tmp_path):
    """Even if demo_mode=True is passed, the engine uses the verified DEM rather than fabricating a synthetic cosine curve."""
    path = _write_dem(tmp_path, -89.9, 0.0, np.zeros((201, 201), dtype=np.float32), synthetic=False)
    res = SimulationEngine(dem_dir=path).run("shackleton", -89.9, 0.0, "2026-11-14T12:00:00Z", 2, 6, 6.0, 0.25, True)
    assert res["status"] == "terrain_aware" and res["is_demo"] is False
    assert res["data_source"] == "real_engine"


def test_bundled_nasa_lola_dem_executes_terrain_aware_and_verifies_geodesy():
    """Explicit test coverage for the bundled LDEM_80S_80MPP_ADJ.TIF on the production SimulationEngine."""
    engine = SimulationEngine()
    res = engine.run("shackleton", -89.9, 0.0, "2026-11-14T12:00:00Z", 2, 6, 6.0, 0.25, False)
    assert res["status"] == "terrain_aware"
    assert res["data_source"] == "real_engine"
    assert res["is_demo"] is False
    assert res["terrain_info"]["dem_product"] == "LDEM_80S_80MPP_ADJ"
    assert res["terrain_info"]["is_synthetic_benchmark"] is False
    assert res["terrain_info"]["geodetic_control_verification"]["all_passed"] is True
    assert "slope_total_deg" in res["terrain_info"]["pad_scale_topography"]
    assert res["validation_report"]["status"] == "terrain_aware_real_data"


def test_design_lab_sensitivity_is_reproducible_and_disclosed():
    from services.mission_design_lab_service import build_design_lab
    a = build_design_lab()["sensitivity"]
    b = build_design_lab()["sensitivity"]
    assert a == b
    assert a["draws"] >= 1000
    assert sum(r["top_rank_share_pct"] for r in a["regions"]) == pytest.approx(100.0, abs=0.5)
    assert "validity of the underlying archive" in a["interpretation"]
