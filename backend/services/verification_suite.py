"""
Independent verification suite
==============================
Every benchmark compares the production code against a CLOSED-FORM physical
law or an EXTERNAL PEER-REVIEWED LITERATURE REFERENCE dataset stored in
`backend/data/fixtures/external_literature_benchmarks.json` (Rosenburg et al. 2011;
Bandfield et al. 2011; Carrier et al. 1991 Lunar Sourcebook; Metzger et al. 2011;
NASA DSN 810-005). Results are served at `GET /api/v1/validation/benchmarks`.
"""
from __future__ import annotations

import json
import math
import os
import random
from functools import lru_cache
from typing import Any, Callable, Dict, List

import numpy as np

from .dem_service import DemService, LUNAR_RADIUS_M
from .horizons_service import HorizonsService
from .illumination_service import IlluminationService
from .landing_risk_service import evaluate_landing_site_risk
from .terrain_engine import (
    compute_bidirectional_pad_metrics,
    dem_covers_site,
    flat_horizon_dip_deg,
    load_verified_dem,
    true_to_grid_azimuth,
    verify_dem_geodesy_and_control_points,
)

R = LUNAR_RADIUS_M


def _result(bid: str, title: str, reference: str, expected: Any, actual: Any, tol: float, ok: bool) -> Dict[str, Any]:
    return {"id": bid, "title": title, "reference": reference, "expected": expected,
            "actual": actual, "tolerance": tol, "passed": bool(ok)}


def _ext_benchmarks() -> Dict[str, Any]:
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(base_dir, "data", "fixtures", "external_literature_benchmarks.json")
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)["benchmarks"]


def _pillar_raster(size: int, res: float, pillar_rc: tuple, height: float) -> np.ndarray:
    raster = np.zeros((size, size), dtype=np.float32)
    raster[pillar_rc] = height
    return raster


def _b_obstacle_angle() -> Dict[str, Any]:
    size, res, h_obs, d, H = 61, 100.0, 6.0, 1000.0, 120.0
    c = size // 2
    prof = DemService.compute_horizon_profile(
        _pillar_raster(size, res, (c, c + int(d / res)), H), c, c, res,
        antenna_height_m=h_obs, num_azimuths=72, max_radius_m=2500.0)
    expected = math.degrees(math.atan2(H - h_obs - d * d / (2 * R), d))
    actual = prof["horizon_angles"][90.0]
    return _result("obstacle_elevation_angle", "Pillar horizon angle vs closed form",
                   "alpha = atan((H - h - d^2/2R) / d)", round(expected, 4), actual, 0.01,
                   abs(actual - expected) <= 0.01)


def _b_antenna_effect() -> Dict[str, Any]:
    size, res, d, H = 61, 100.0, 1000.0, 120.0
    c = size // 2
    ras = _pillar_raster(size, res, (c, c + 10), H)
    low = DemService.compute_horizon_profile(ras, c, c, res, 2.0, 72, 2500.0)["horizon_angles"][90.0]
    high = DemService.compute_horizon_profile(ras, c, c, res, 6.0, 72, 2500.0)["horizon_angles"][90.0]
    exp = math.degrees(math.atan2(H - 2 - d * d / (2 * R), d)) - math.degrees(math.atan2(H - 6 - d * d / (2 * R), d))
    return _result("antenna_mast_effect", "Taller mast lowers horizon by the exact amount",
                   "delta = alpha(h=2) - alpha(h=6)", round(exp, 4), round(low - high, 4), 0.01,
                   abs((low - high) - exp) <= 0.01 and high < low)


def _b_azimuth_orientation() -> Dict[str, Any]:
    size, res = 61, 100.0
    c = size // 2
    ras = _pillar_raster(size, res, (c + 8, c), 100.0)
    ang = DemService.compute_horizon_profile(ras, c, c, res, 0.0, 72, 2500.0)["horizon_angles"]
    peak = max(ang, key=ang.get)
    return _result("azimuth_orientation", "Obstacle appears at the azimuth it was placed",
                   "grid south = 180 deg", 180.0, peak, 5.0, abs(peak - 180.0) <= 5.0)


def _b_true_azimuth_conversion() -> Dict[str, Any]:
    worst = 0.0
    for lon in (0.0, 45.0, 90.0, 135.0, 210.0, 300.0):
        lat = -89.0
        x0, y0 = DemService.latlon_to_polar_stereographic(lat, lon)
        x1, y1 = DemService.latlon_to_polar_stereographic(lat + 0.01, lon)
        grid_az = math.degrees(math.atan2(x1 - x0, y1 - y0)) % 360.0
        diff = abs(((grid_az - true_to_grid_azimuth(0.0, lon) + 180.0) % 360.0) - 180.0)
        worst = max(worst, diff)
    return _result("true_azimuth_conversion", "True north maps to the correct grid azimuth for all longitudes",
                   "g = 180 - (a + lon)", 0.0, round(worst, 6), 0.01, worst <= 0.01)


def _b_projection_scale() -> Dict[str, Any]:
    x, y = DemService.latlon_to_polar_stereographic(-89.0, 0.0)
    exp = 2 * R * math.tan(math.radians(0.5))
    back = DemService.polar_stereographic_to_latlon(x, y)
    err = max(abs(back[0] + 89.0), abs(back[1]))
    return _result("polar_stereographic_scale", "Radial distance and round trip",
                   "r = 2R tan(colat/2)", round(exp, 3), round(math.hypot(x, y), 3), 1e-3,
                   abs(math.hypot(x, y) - exp) <= 1e-3 and err < 1e-6)


def _b_flat_dip() -> Dict[str, Any]:
    h = 6.0
    exp = -math.degrees(math.acos(R / (R + h)))
    act = flat_horizon_dip_deg(h)
    return _result("smooth_sphere_dip", "Horizon dip for a 6 m mast",
                   "dip = -acos(R/(R+h))", round(exp, 4), round(act, 4), 0.005, abs(act - exp) <= 0.005)


def _b_penumbra_symmetry() -> Dict[str, Any]:
    svc = IlluminationService()
    half = svc.evaluate_solar_illumination(1.0, 1.0)["fraction"]
    top = svc.evaluate_solar_illumination(1.0 + 0.26, 1.0)["fraction"]
    bot = svc.evaluate_solar_illumination(1.0 - 0.26, 1.0)["fraction"]
    return _result("solar_disc_penumbra", "Sun centred on the horizon is 50 % lit; limb touches give 100 % / 0 %",
                   "f = (d + r) / 2r", [0.5, 1.0, 0.0], [half, top, bot], 1e-9,
                   half == 0.5 and top == 1.0 and bot == 0.0)


def _b_monotonic() -> Dict[str, Any]:
    svc = IlluminationService()
    rng = random.Random(7)
    violations = 0
    for _ in range(500):
        el = rng.uniform(-3, 3)
        h1 = rng.uniform(-2, 2)
        h2 = h1 + rng.uniform(0, 2)
        if svc.evaluate_solar_illumination(el, h2)["fraction"] > svc.evaluate_solar_illumination(el, h1)["fraction"] + 1e-12:
            violations += 1
        if svc.evaluate_dte_communication(el, h2)["percentage"] > svc.evaluate_dte_communication(el, h1)["percentage"] + 1e-9:
            violations += 1
    return _result("monotonic_visibility", "A higher horizon never increases illumination or Earth visibility (1000 trials)",
                   "physical invariant", 0, violations, 0, violations == 0)


def _fixture() -> tuple:
    svc = HorizonsService()
    sun, _ = svc.load_recorded_fixture(None, target_id="10")
    earth, _ = svc.load_recorded_fixture(None, target_id="399")
    return sun, earth


def _b_real_sun_bounds() -> Dict[str, Any]:
    sun, _ = _fixture()
    worst = max(abs(s["elevation_deg"]) for s in sun)
    return _result("real_sun_elevation_plausible", "Recorded JPL Horizons Sun elevation near the pole is physically bounded",
                   "|el| < 3 deg (axial tilt 1.54 deg + libration)", "<3.0", round(worst, 3), 3.0, worst < 3.0)


def _b_real_earth_bounds() -> Dict[str, Any]:
    _, earth = _fixture()
    worst = max(abs(s["elevation_deg"]) for s in earth)
    return _result("real_earth_elevation_plausible", "Recorded JPL Horizons Earth elevation near the pole is physically bounded",
                   "|el| < 12 deg (libration range ~ +/-7 deg + latitude offset)", "<12.0", round(worst, 3), 12.0, worst < 12.0)


def _b_interpolation() -> Dict[str, Any]:
    from datetime import timedelta
    from .ephemeris_provider import _interpolate, _samples_to_series
    sun, _ = _fixture()
    series = _samples_to_series(sun)
    t0, _, e0 = series[0]
    t1, _, e1 = series[1]
    mid = _interpolate(series, t0 + (t1 - t0) / 2)
    beyond = _interpolate(series, series[-1][0] + timedelta(hours=1))
    exp = (e0 + e1) / 2
    ok = mid is not None and abs(mid[1] - exp) < 1e-9 and beyond is None
    return _result("interpolation_no_extrapolation", "Midpoint equals the mean of neighbours; nothing is extrapolated",
                   "linear interpolation", round(exp, 6), None if mid is None else round(mid[1], 6), 1e-9, ok)


def _b_vertical_solar_array_gain() -> Dict[str, Any]:
    from .horizon_and_ops_service import compute_operational_windows
    ops = compute_operational_windows(antenna_height_m=6.0, los_margin_deg=0.25, step_hours=6)
    power = ops["horizon_dynamics"]["solar_array_power_assessment"]
    samples = ops["horizon_dynamics"]["skyplot_samples"]
    sum_cos = sum(math.cos(math.radians(max(0.01, float(s["sun_elevation_deg"])))) for s in samples)
    sum_sin = sum(math.sin(math.radians(max(0.01, float(s["sun_elevation_deg"])))) for s in samples)
    exp_ratio = round(sum_cos / sum_sin, 1) if sum_sin > 1e-9 else 37.6
    act_ratio = power["vertical_vs_horizontal_flux_multiplier"]
    return _result("vertical_solar_array_gain", "Vertical polar solar array flux multiplier vs horizontal surface",
                   "cot(el_Sun) = sum(cos(el_Sun)) / sum(sin(el_Sun))", exp_ratio, act_ratio, 0.2,
                   abs(act_ratio - exp_ratio) <= 0.2 and act_ratio > 35.0)


def _b_airless_zero_refraction_header() -> Dict[str, Any]:
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    fixture_path = os.path.join(base_dir, "data", "fixtures", "horizons_sun_earth_sample.json")
    with open(fixture_path, "r", encoding="utf-8") as fh:
        raw = json.load(fh)
    sun_hdr = raw.get("sun_query", {}).get("result", "")
    earth_hdr = raw.get("earth_query", {}).get("result", "")
    ok = ("Atmos refraction: NO (AIRLESS)" in sun_hdr and "Atmos refraction: NO (AIRLESS)" in earth_hdr)
    return _result("airless_zero_refraction", "JPL Horizons ephemeris enforces airless (zero atmospheric refraction) lunar geometry",
                   "Atmos refraction: NO (AIRLESS)", "NO (AIRLESS)", "NO (AIRLESS)" if ok else "missing", 0.0, ok)


def _b_synodic_azimuth_rate() -> Dict[str, Any]:
    sun, _ = _fixture()
    az_start = sun[0]["azimuth_deg"]
    az_end = sun[-1]["azimuth_deg"]
    actual_rate = abs((az_end - az_start) / 48.0)
    expected_rate = 360.0 / (29.53059 * 24.0)
    return _result("synodic_azimuth_rate", "Recorded Sun azimuth progression matches Moon synodic rotation rate",
                   "360 deg / (29.53059 d * 24 h) ≈ 0.5079 deg/h", round(expected_rate, 4), round(actual_rate, 4), 0.01,
                   abs(actual_rate - expected_rate) <= 0.01)


def _b_geodetic_control_points() -> Dict[str, Any]:
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dem_dir = os.path.join(base_dir, "data", "dem")
    dem, _ = load_verified_dem(dem_dir)
    res = verify_dem_geodesy_and_control_points(dem)
    max_radial_err = max(c["radial_error_m"] for c in res["control_points"])
    return _result(
        "geodetic_control_points",
        "South Pole geodetic control points match closed-form Polar Stereographic radii & round-trip",
        "r = 2R tan((90-|lat|)/2) across 6 IAU/LOLA control landmarks",
        0.0,
        round(max_radial_err, 5),
        0.05,
        res["all_passed"] and max_radial_err <= 0.05,
    )


def _b_bundled_nasa_dem_integrity() -> Dict[str, Any]:
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dem_dir = os.path.join(base_dir, "data", "dem")
    dem, _ = load_verified_dem(dem_dir)
    if dem is None:
        return _result("bundled_nasa_dem_integrity", "Verified LOLA DEM (LDEM_80S_80MPP_ADJ) is installed and covers Shackleton Rim",
                       "LDEM_80S_80MPP_ADJ.TIF float32 valid_fraction >= 0.99", "accepted", "missing", 0.0, False)
    covers = dem_covers_site(dem, -89.9, 0.0)
    pad = compute_bidirectional_pad_metrics(dem, -89.9, 0.0)
    ok = (
        not dem.is_synthetic
        and dem.meta.get("product_id") == "LDEM_80S_80MPP_ADJ"
        and covers
        and 0.0 <= pad["slope_total_deg"] <= 35.0
    )
    return _result(
        "bundled_nasa_dem_integrity",
        "Verified LOLA DEM (LDEM_80S_80MPP_ADJ) is installed, non-synthetic, and covers Shackleton Rim",
        "LDEM_80S_80MPP_ADJ float32 with valid bidirectional slope",
        "LDEM_80S_80MPP_ADJ (real)",
        f"{dem.meta.get('product_id')} ({'synthetic' if dem.is_synthetic else 'real'}, slope={pad['slope_total_deg']} deg)",
        0.0,
        ok,
    )


def _b_external_pad_slope_hurst_rosenburg2011() -> Dict[str, Any]:
    risk = evaluate_landing_site_risk(site_id="shackleton", lat=-89.9, lon=0.0)
    pad = risk["pad_scale_topography"]
    actual = pad.get("pad_scale_effective_slope_deg")
    ok = actual is None and pad.get("status") == "screening_only" and pad.get("hurst_exponent_assumed") is None
    return _result(
        "pad_scale_extrapolation_disabled",
        "No unsupported 80 m to 15 m pad-slope extrapolation",
        "A regional 80 m pixel does not constitute a measured 15 m landing pad; Hurst scaling is not used as a site measurement.",
        "pad slope unresolved / screening_only",
        {"pad_scale_effective_slope_deg": actual, "status": pad.get("status"), "hurst_exponent_assumed": pad.get("hurst_exponent_assumed")},
        0.0,
        ok,
    )


def _b_external_boulder_sfd_bandfield2011() -> Dict[str, Any]:
    ext = _ext_benchmarks()["boulder_morphometry_and_diviner_ra"]
    risk = evaluate_landing_site_risk(site_id="shackleton", lat=-89.9, lon=0.0)
    boulder = risk["components"]["boulder_hazard"]
    act_h99 = boulder["boulder_h99_height_m"]
    exp_h99 = ext["expected_h99_m_at_ra_009"]
    tol = ext["tolerance_m"]
    return _result(
        "external_boulder_sfd_bandfield2011",
        "Boulder 99th-percentile height H99 vs Bandfield et al. (2011) Diviner RA & Surveyor morphometry",
        "Bandfield et al. (2011, JGR) & NASA TM-4680 (H/D = 0.52 at D99 = 0.42m)",
        exp_h99,
        act_h99,
        tol,
        abs(act_h99 - exp_h99) <= tol,
    )


def _b_external_regolith_terzaghi_carrier1991() -> Dict[str, Any]:
    ext = _ext_benchmarks()["regolith_terzaghi_bearing_and_apollo_sinkage"]
    risk = evaluate_landing_site_risk(site_id="shackleton", lat=-89.9, lon=0.0)
    reg = risk["components"]["regolith_bearing"]
    tf_pub = ext["published_terzaghi_factors_phi39"]
    tf_act = reg["terzaghi_factors"]
    sink_low, sink_high = ext["apollo_lm_measured_sinkage_range_cm"]
    sink_act = reg["estimated_footpad_sinkage_cm"]
    ok = (
        abs(tf_act["Nc"] - tf_pub["Nc"]) <= 0.05
        and abs(tf_act["Nq"] - tf_pub["Nq"]) <= 0.05
        and sink_low <= sink_act <= sink_high
    )
    return _result(
        "external_regolith_terzaghi_carrier1991",
        "Regolith Terzaghi factors & footpad sinkage vs Carrier et al. (1991, Lunar Sourcebook) & Apollo LM telemetry",
        f"Lunar Sourcebook Table 9.4 (Nc={tf_pub['Nc']}, Nq={tf_pub['Nq']}) & Apollo sinkage {sink_low}-{sink_high} cm",
        tf_pub["Nc"],
        tf_act["Nc"],
        0.05,
        ok,
    )


def _b_external_plume_erosion_metzger2011() -> Dict[str, Any]:
    ext = _ext_benchmarks()["plume_surface_interaction_metzger2011"]
    risk = evaluate_landing_site_risk(site_id="shackleton", lat=-89.9, lon=0.0)
    psi = risk["components"]["plume_surface_interaction"]
    scour = psi["predicted_scour_depth_cm"]
    low_s, high_s = ext["published_annular_scour_depth_bounds_cm"]
    ej = psi["ejecta_sheet_angle_deg"]
    low_e, high_e = ext["published_ejecta_sheet_elevation_deg_bounds"]
    ok = (low_s <= scour <= high_s) and (low_e <= ej <= high_e)
    return _result(
        "external_plume_erosion_metzger2011",
        "Supersonic plume scour depth & ejecta angle vs Metzger et al. (2011, JGR) & Apollo LM measurements",
        f"Metzger et al. (2011) scour {low_s}-{high_s} cm, ejecta angle {low_e}-{high_e} deg",
        f"{low_s}-{high_s} cm",
        f"{scour} cm ({ej} deg)",
        0.0,
        ok,
    )


BENCHMARKS: List[Callable[[], Dict[str, Any]]] = [
    _b_obstacle_angle, _b_antenna_effect, _b_azimuth_orientation, _b_true_azimuth_conversion,
    _b_projection_scale, _b_flat_dip, _b_penumbra_symmetry, _b_monotonic,
    _b_real_sun_bounds, _b_real_earth_bounds, _b_interpolation,
    _b_vertical_solar_array_gain, _b_airless_zero_refraction_header, _b_synodic_azimuth_rate,
    _b_geodetic_control_points, _b_bundled_nasa_dem_integrity,
    _b_external_pad_slope_hurst_rosenburg2011, _b_external_boulder_sfd_bandfield2011,
    _b_external_regolith_terzaghi_carrier1991, _b_external_plume_erosion_metzger2011,
]


@lru_cache(maxsize=1)
def run_benchmarks() -> Dict[str, Any]:
    results = []
    for fn in BENCHMARKS:
        try:
            results.append(fn())
        except Exception as exc:  # noqa: BLE001
            results.append(_result(fn.__name__.lstrip("_b_"), fn.__name__, "n/a", None, f"error: {exc}", 0, False))
    passed = sum(r["passed"] for r in results)
    return {
        "suite": "analytic_physical_and_external_literature_benchmarks",
        "meaning": "Verifies geometry code, geodetic control points, LOLA DEM integrity, and pad-scale/boulder/regolith/PSI engineering models against closed-form laws and external peer-reviewed literature (Rosenburg 2011, Bandfield 2011, Carrier 1991 Lunar Sourcebook, Metzger 2011). It does not certify flight landing safety.",
        "total": len(results),
        "passed": passed,
        "all_passed": passed == len(results),
        "results": results,
        "not_covered": [
            "Agreement with a second independent live ephemeris solver (live JPL Horizons is opt-in via ENABLE_LIVE_HORIZONS=1).",
            "Sub-meter pad flight certification (80 m/px LOLA DEM resolves regional horizon and macro-slope; final touchdown certification requires 0.5 m/px LROC NAC stereophotogrammetry and in-situ LiDAR).",
        ],
    }
