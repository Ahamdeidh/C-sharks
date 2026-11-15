"""
Integrated Pad-Scale Landing Risk & Engineering Assessment Service
==================================================================
Evaluates five engineering domains with explicit per-metric source classification,
operating resolution boundaries, and independent cross-validation against
published peer-reviewed lunar literature (Rosenburg et al. 2011; Bandfield et al.
2011; Carrier et al. 1991 Lunar Sourcebook; Metzger et al. 2011; NASA DSN 810-005):

1. Bidirectional Pad-Scale Slope & Roughness (80 m/px LOLA DEM gradient + Hurst
   fractal scaling H=0.75 to 15 m lander footprint).
2. Boulder Hazard & Under-Deck Leg Clearance (LRO Diviner rock abundance + LROC
   NAC / Surveyor cumulative boulder size-frequency distribution).
3. Regolith Geotechnical Bearing Capacity & Sinkage (Lunar Sourcebook Terzaghi
   bearing capacity vs. dynamic touchdown contact pressure & Apollo LM sinkage).
4. Rocket Plume-Surface Interaction (PSI) (Metzger et al. 2011 supersonic exhaust
   wall shear stress vs. critical regolith erosion threshold & scour depth).
5. Full Direct-to-Earth (DTE) X-Band RF Link Budget (NASA DSN 810-005 34 m BWG
   link budget at 8.42 GHz across 384,400 km).
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from .terrain_engine import compute_bidirectional_pad_metrics, dem_covers_site, load_verified_dem

LUNAR_GRAVITY_M_S2 = 1.622
SPEED_OF_LIGHT_M_S = 299792458.0
MEAN_EARTH_MOON_DIST_M = 384400000.0
BOLTZMANN_DBW_K_HZ = -228.60

SITE_ENGINEERING_PROFILES: Dict[str, Dict[str, Any]] = {
    "shackleton": {
        "site_name": "Shackleton Crater Rim",
        "rock_abundance_fraction": 0.009,
        "boulder_d99_m": 0.42,
        "boulder_density_per_ha": 18.0,
        "regolith_density_kg_m3": 1580.0,
        "regolith_cohesion_kpa": 0.85,
        "regolith_friction_angle_deg": 39.0,
        "fallback_slope_ew_deg": 3.8,
        "fallback_slope_ns_deg": -5.1,
        "earth_mean_el_deg": -2.79,
        "provenance_tier": "curated_assumption_not_site_extracted_diviner",
        "rock_abundance_provenance": "[Curated Assumption] Site-specific constant; not extracted from a Diviner raster. The cited literature supports contextual polar-highland ranges, not this site value.",
    },
    "malapert": {
        "site_name": "Malapert Massif Ridge",
        "rock_abundance_fraction": 0.006,
        "boulder_d99_m": 0.34,
        "boulder_density_per_ha": 11.0,
        "regolith_density_kg_m3": 1560.0,
        "regolith_cohesion_kpa": 0.78,
        "regolith_friction_angle_deg": 38.0,
        "fallback_slope_ew_deg": 2.9,
        "fallback_slope_ns_deg": -3.8,
        "earth_mean_el_deg": 4.15,
        "provenance_tier": "curated_assumption_not_site_extracted_diviner",
        "rock_abundance_provenance": "[Curated Assumption] Site-specific constant; not extracted from a Diviner raster. The cited literature supports contextual polar-highland ranges, not this site value.",
    },
    "connecting-ridge": {
        "site_name": "Connecting Ridge",
        "rock_abundance_fraction": 0.008,
        "boulder_d99_m": 0.39,
        "boulder_density_per_ha": 15.0,
        "regolith_density_kg_m3": 1550.0,
        "regolith_cohesion_kpa": 0.72,
        "regolith_friction_angle_deg": 37.5,
        "fallback_slope_ew_deg": -5.4,
        "fallback_slope_ns_deg": 6.0,
        "earth_mean_el_deg": -1.40,
        "provenance_tier": "curated_assumption_not_site_extracted_diviner",
        "rock_abundance_provenance": "[Curated Assumption] Site-specific constant; not extracted from a Diviner raster. The cited literature supports contextual polar-highland ranges, not this site value.",
    },
    "de-gerlache": {
        "site_name": "de Gerlache Rim 1",
        "rock_abundance_fraction": 0.011,
        "boulder_d99_m": 0.46,
        "boulder_density_per_ha": 22.0,
        "regolith_density_kg_m3": 1520.0,
        "regolith_cohesion_kpa": 0.65,
        "regolith_friction_angle_deg": 36.5,
        "fallback_slope_ew_deg": -6.2,
        "fallback_slope_ns_deg": 6.8,
        "earth_mean_el_deg": -1.85,
        "provenance_tier": "curated_assumption_not_site_extracted_diviner",
        "rock_abundance_provenance": "[Curated Assumption] Site-specific constant; not extracted from a Diviner raster. The cited literature supports contextual polar-highland ranges, not this site value.",
    },
    "haworth": {
        "site_name": "Haworth Crater Rim",
        "rock_abundance_fraction": 0.013,
        "boulder_d99_m": 0.51,
        "boulder_density_per_ha": 26.0,
        "regolith_density_kg_m3": 1490.0,
        "regolith_cohesion_kpa": 0.58,
        "regolith_friction_angle_deg": 35.5,
        "fallback_slope_ew_deg": 7.5,
        "fallback_slope_ns_deg": -8.7,
        "earth_mean_el_deg": -2.10,
        "provenance_tier": "curated_assumption_not_site_extracted_diviner",
        "rock_abundance_provenance": "[Curated Assumption] Site-specific constant; not extracted from a Diviner raster. The cited literature supports contextual polar-highland ranges, not this site value.",
    },
}


def _load_external_benchmarks() -> Dict[str, Any]:
    path = Path(__file__).parent.parent / "data" / "fixtures" / "external_literature_benchmarks.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _terzaghi_factors(phi_deg: float) -> Dict[str, float]:
    """Standard Terzaghi bearing capacity factors Nc, Nq, Ngamma for friction angle phi."""
    phi = math.radians(max(15.0, min(50.0, phi_deg)))
    nq = math.exp(math.pi * math.tan(phi)) * (math.tan(math.pi / 4.0 + phi / 2.0) ** 2)
    nc = (nq - 1.0) / math.tan(phi)
    ngamma = 2.0 * (nq + 1.0) * math.tan(phi)
    return {"Nc": round(nc, 2), "Nq": round(nq, 2), "Ngamma": round(ngamma, 2)}


def evaluate_landing_site_risk(
    site_id: str = "shackleton",
    lat: float = -89.9,
    lon: float = 0.0,
    antenna_height_m: float = 6.0,
    los_margin_deg: float = 0.25,
    lander_mass_kg: float = 1850.0,
    lander_max_tilt_deg: float = 12.0,
    lander_belly_clearance_m: float = 0.65,
    footpad_radius_m: float = 0.25,
    num_footpads: int = 4,
    descent_thrust_n: float = 15000.0,
    nozzle_cutoff_height_m: float = 2.0,
    rf_tx_power_w: float = 15.0,
    rf_antenna_diam_m: float = 0.60,
    rf_data_rate_mbps: float = 2.0,
    strict_field_certification_only: bool = False,
    custom_engineering_inputs: Optional[Dict[str, Any]] = None,
    dem_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Evaluates pad-scale bidirectional slope, boulder height clearance, regolith
    geotechnical bearing capacity, rocket plume-surface interaction (PSI), and
    Direct-to-Earth X-band RF link budget, with explicit per-value provenance,
    resolution limits, and model-consistency comparisons against cited literature.
    """
    profile = SITE_ENGINEERING_PROFILES.get(site_id, SITE_ENGINEERING_PROFILES["shackleton"]).copy()
    if custom_engineering_inputs:
        profile.update(custom_engineering_inputs)

    if dem_dir is None:
        dem_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "dem")
    verified_dem, _ = load_verified_dem(dem_dir)
    site_dem_covered = bool(verified_dem is not None and dem_covers_site(verified_dem, lat, lon, radius_m=800.0))
    ext_ref = _load_external_benchmarks()["benchmarks"]

    # -------------------------------------------------------------------------
    # 1. Bidirectional Pad-Scale Topography (Real DEM when covered, else profile)
    # -------------------------------------------------------------------------
    if site_dem_covered:
        pad_topo = compute_bidirectional_pad_metrics(verified_dem, lat, lon, lander_pad_span_m=15.0)
        pad_source = "real_lola_dem_bidirectional_gradient"
        pad_source_badge = f"LOLA DEM source-scale gradient ({verified_dem.meta['resolution_m_per_px']} m/px); no Hurst extrapolation"
    else:
        ew = float(profile["fallback_slope_ew_deg"])
        ns = float(profile["fallback_slope_ns_deg"])
        tot = math.degrees(math.atan(math.hypot(math.tan(math.radians(ew)), math.tan(math.radians(ns)))))
        hurst = None
        amp = None
        pad_topo = {
            "dem_resolution_m": 80.0,
            "lander_pad_span_m": 15.0,
            "slope_east_west_deg": round(ew, 2),
            "slope_north_south_deg": round(ns, 2),
            "slope_total_deg": round(tot, 2),
            "downslope_aspect_true_az_deg": round(math.degrees(math.atan2(-ew, -ns)) % 360.0, 1),
            "hurst_exponent_assumed": hurst,
            "pad_scale_slope_amplification": amp,
            "pad_scale_effective_slope_deg": None,
            "measurement_status": "screening_only_pad_scale_unresolved",
            "resolution_limitation_note": "Regional slope is a contextual screening proxy; no 15 m field measurement or Hurst extrapolation is claimed.",
        }
        pad_source = "regional_lola_reference_profile"
        pad_source_badge = "Regional reference profile; screening only"

    effective_pad_slope = pad_topo.get("pad_scale_effective_slope_deg")
    tilt_margin_deg = round(lander_max_tilt_deg - effective_pad_slope, 2) if effective_pad_slope is not None else None
    has_site_pad_survey = bool((custom_engineering_inputs or {}).get("in_situ_slope_survey"))
    slope_status = ("screening_only" if not has_site_pad_survey else ("pass" if tilt_margin_deg is not None and tilt_margin_deg >= 2.0 else ("caution" if tilt_margin_deg is not None and tilt_margin_deg >= 0.0 else "fail")))

    dem_res = float(verified_dem.meta.get("resolution_m_per_px", 80.0)) if verified_dem is not None else 80.0
    pixel_area = dem_res * dem_res
    pad_area = 15.0 * 15.0
    resolution_boundary = {
        "dem_pixel_size_m": dem_res,
        "dem_pixel_area_m2": pixel_area,
        "lander_pad_span_m": 15.0,
        "lander_pad_area_m2": 225.0,
        "pixel_to_pad_area_ratio": round(pixel_area / pad_area, 3),
        "warning_headline": f"Spatial resolution boundary ({dem_res:g} m/px): screening only, not landing certification",
        "warning_detail": (
            f"One DEM pixel covers {pixel_area:g} m² versus an illustrative 15 m pad footprint ({pad_area:g} m²). "
            "The source-scale gradient does not resolve sub-pixel hazards. No Hurst extrapolation or certification is claimed; "
            "local LROC imagery and field/engineering measurements remain necessary."
        ),
    }

    has_custom_survey = bool(custom_engineering_inputs)
    if strict_field_certification_only and not has_custom_survey:
        return {
            "service": "landing_site_risk_and_rf_assessment",
            "mode": "strict_field_certification_gate",
            "status": "blocked",
            "site_id": site_id,
            "lat_deg": lat,
            "lon_deg": lon,
            "resolution_and_certification_boundary": resolution_boundary,
        "dem_coverage": {"covered": site_dem_covered, "label": f"{verified_dem.meta.get('product_id')} ({dem_res:g} m/px)" if site_dem_covered else "regional DEM unavailable at requested point", "warning": None if site_dem_covered else "Requested site/pad is outside verified DEM coverage or has NoData; fallback values are screening proxies, not site-specific DEM measurements."},
            "pad_scale_topography": {
                **pad_topo,
                "source": pad_source,
                "source_badge": pad_source_badge,
                "limitation_badge": "دقة 80 م/بكسل إقليمية؛ لا تغني عن مسح 0.5 م/بكسل لمنصة الهبوط",
                "status": slope_status,
                "tilt_margin_deg": tilt_margin_deg,
            },
            "components": {
                "boulder_hazard": {
                    "status": "blocked",
                    "reason": "Sub-meter LROC NAC boulder inventory map is required for flight pad certification.",
                    "required_inputs": ["boulder_d99_m", "boulder_density_per_ha", "lander_belly_clearance_m"],
                },
                "regolith_bearing": {
                    "status": "blocked",
                    "reason": "In-situ geotechnical cone-penetrometer parameters are required for flight pad certification.",
                    "required_inputs": ["regolith_cohesion_kpa", "regolith_friction_angle_deg", "regolith_density_kg_m3"],
                },
                "plume_surface_interaction": {
                    "status": "blocked",
                    "reason": "Engine nozzle plume CFD shear profile is required for flight certification.",
                    "required_inputs": ["descent_thrust_n", "nozzle_cutoff_height_m"],
                },
                "rf_link_budget": {
                    "status": "blocked",
                    "reason": "Flight transponder EIRP and DSN station schedule are required for operational link certification.",
                    "required_inputs": ["rf_tx_power_w", "rf_antenna_diam_m", "rf_data_rate_mbps"],
                },
            },
        }

    # -------------------------------------------------------------------------
    # 2. Boulder Distribution & Under-Deck Leg Clearance
    # -------------------------------------------------------------------------
    d99_m = float(profile["boulder_d99_m"])
    h99_m = round(0.52 * d99_m, 3)
    leg_stroke_allowance_m = 0.15
    effective_clearance_m = round(lander_belly_clearance_m - leg_stroke_allowance_m, 3)
    boulder_clearance_margin_m = round(effective_clearance_m - h99_m, 3)
    pad_area_ha = (math.pi * (12.5 ** 2)) / 10000.0
    expected_hazard_boulders = float(profile["boulder_density_per_ha"]) * pad_area_ha * max(0.05, d99_m / max(0.2, effective_clearance_m))
    prob_clean_pad_pct = round(100.0 * math.exp(-expected_hazard_boulders * 0.18), 1)
    # Regional priors and assumed clearance are not a georeferenced local boulder map.
    boulder_status = "screening_only"
    prob_clean_pad_pct = None

    # -------------------------------------------------------------------------
    # 3. Regolith Geotechnical Bearing Capacity & Footpad Sinkage (Terzaghi)
    # -------------------------------------------------------------------------
    rho = float(profile["regolith_density_kg_m3"])
    c_kpa = float(profile["regolith_cohesion_kpa"])
    phi_deg = float(profile["regolith_friction_angle_deg"])
    tf = _terzaghi_factors(phi_deg)
    assumed_embedment_m = 0.04
    q_ult_kpa = round(
        1.3 * c_kpa * tf["Nc"]
        + (rho * LUNAR_GRAVITY_M_S2 * assumed_embedment_m / 1000.0) * tf["Nq"]
        + 0.6 * (rho * LUNAR_GRAVITY_M_S2 * footpad_radius_m / 1000.0) * tf["Ngamma"],
        2,
    )
    dynamic_load_factor = 2.2
    total_touchdown_force_n = lander_mass_kg * LUNAR_GRAVITY_M_S2 * dynamic_load_factor
    total_pad_area_m2 = max(1, num_footpads) * math.pi * (footpad_radius_m ** 2)
    q_contact_kpa = round((total_touchdown_force_n / total_pad_area_m2) / 1000.0, 2)
    bearing_safety_factor = round(q_ult_kpa / max(0.01, q_contact_kpa), 2)
    estimated_sinkage_cm = round(max(0.8, min(18.0, (q_contact_kpa / max(1.0, q_ult_kpa)) * 22.0)), 2)
    regolith_status = "screening_only" if not (custom_engineering_inputs or {}).get("in_situ_geotechnical_log") else ("pass" if bearing_safety_factor >= 3.0 else ("caution" if bearing_safety_factor >= 1.5 else "fail"))

    # -------------------------------------------------------------------------
    # 4. Rocket Plume-Surface Interaction (PSI) & Regolith Scouring
    # -------------------------------------------------------------------------
    impingement_pressure_pa = descent_thrust_n / (2.0 * math.pi * (max(0.5, nozzle_cutoff_height_m) ** 2))
    wall_shear_stress_pa = round(0.14 * impingement_pressure_pa, 1)
    critical_erosion_shear_pa = round(c_kpa * 18.0 + 12.0 * math.tan(math.radians(phi_deg)), 1)
    scour_depth_cm = round(max(0.5, (wall_shear_stress_pa / max(1.0, critical_erosion_shear_pa)) * 1.85), 2)
    ejecta_sheet_elevation_deg = 2.4
    transient_dust_optical_depth = round(min(2.5, 0.12 * (descent_thrust_n / 10000.0) / max(0.8, nozzle_cutoff_height_m)), 3)
    psi_status = "pass" if scour_depth_cm <= 6.0 else ("caution" if scour_depth_cm <= 12.0 else "fail")

    # -------------------------------------------------------------------------
    # 5. Direct-to-Earth (DTE) X-Band RF Link Budget
    # -------------------------------------------------------------------------
    freq_x_hz = 8.42e9
    wavelength_x_m = SPEED_OF_LIGHT_M_S / freq_x_hz
    fspl_x_db = round(20.0 * math.log10(4.0 * math.pi * MEAN_EARTH_MOON_DIST_M / wavelength_x_m), 2)
    tx_power_dbw = round(10.0 * math.log10(max(0.1, rf_tx_power_w)), 2)
    antenna_eff = 0.58
    tx_gain_dbi = round(10.0 * math.log10(antenna_eff * ((math.pi * rf_antenna_diam_m / wavelength_x_m) ** 2)), 2)
    circuit_and_pointing_loss_db = -2.20
    eirp_dbw = round(tx_power_dbw + tx_gain_dbi + circuit_and_pointing_loss_db, 2)
    dsn_34m_gt_db_k = 68.50
    data_rate_dbhz = round(10.0 * math.log10(max(0.01, rf_data_rate_mbps) * 1e6), 2)
    cn0_dbhz = round(eirp_dbw - fspl_x_db + dsn_34m_gt_db_k - BOLTZMANN_DBW_K_HZ, 2)
    eb_n0_received_db = round(cn0_dbhz - data_rate_dbhz, 2)
    eb_n0_required_ldpc_db = 3.50
    link_margin_when_los_clear_db = round(eb_n0_received_db - eb_n0_required_ldpc_db, 2)

    earth_mean_el = float(profile["earth_mean_el_deg"])
    geometric_los_clear = earth_mean_el >= los_margin_deg
    rf_status = "pass" if (link_margin_when_los_clear_db >= 3.0 and geometric_los_clear) else "caution"

    # -------------------------------------------------------------------------
    # 6. Independent External Literature Cross-Validation Table
    # -------------------------------------------------------------------------
    independent_validation: List[Dict[str, Any]] = [
        {
            "domain": "Pad-Scale Fractal Slope Scaling (80m → 15m)",
            "external_source": ext_ref["pad_scale_fractal_slope"]["citation"],
            "reference_url": ext_ref["pad_scale_fractal_slope"]["url"],
            "published_reference_value": f"Amplification = {ext_ref['pad_scale_fractal_slope']['expected_amplification_factor']}x (H = 0.75 ± 0.03)",
            "model_computed_value": f"Amplification = {pad_topo['pad_scale_slope_amplification']}x (Pad Slope = {pad_topo['pad_scale_effective_slope_deg']}°)",
            "agreement_status": ("not_evaluated_no_pad_scale_measurement" if pad_topo.get("pad_scale_slope_amplification") is None else ("screening_consistency_only_not_independent_validation" if abs(pad_topo["pad_scale_slope_amplification"] - ext_ref["pad_scale_fractal_slope"]["expected_amplification_factor"]) <= 0.01 else "caution")),
        },
        {
            "domain": "Boulder Morphometry (H/D) & Diviner Rock Abundance",
            "external_source": ext_ref["boulder_morphometry_and_diviner_ra"]["citation"],
            "reference_url": ext_ref["boulder_morphometry_and_diviner_ra"]["url"],
            "published_reference_value": "H/D = 0.52 (0.48–0.56); Polar Highland RA = 0.4%–1.8%",
            "model_computed_value": f"H/D = {round(h99_m / d99_m, 2)} (H99 = {h99_m}m for D99 = {d99_m}m; RA = {profile['rock_abundance_fraction'] * 100:.1f}%)",
            "agreement_status": "screening_consistency_only_not_independent_validation" if 0.48 <= (h99_m / d99_m) <= 0.56 else "caution",
        },
        {
            "domain": "Regolith Terzaghi Bearing & Apollo LM Sinkage",
            "external_source": ext_ref["regolith_terzaghi_bearing_and_apollo_sinkage"]["citation"],
            "reference_url": ext_ref["regolith_terzaghi_bearing_and_apollo_sinkage"]["url"],
            "published_reference_value": "Apollo LM sinkage = 1.5–6.0 cm at q = 5–12 kPa; Terzaghi Nc=67.87, Nq=55.96 (φ=39°)",
            "model_computed_value": f"Sinkage = {estimated_sinkage_cm} cm at q = {q_contact_kpa} kPa; q_ult = {q_ult_kpa} kPa",
            "agreement_status": "screening_consistency_only_not_independent_validation" if 1.0 <= estimated_sinkage_cm <= 6.5 else "caution",
        },
        {
            "domain": "Supersonic Plume Scouring & Ejecta Sheet (PSI)",
            "external_source": ext_ref["plume_surface_interaction_metzger2011"]["citation"],
            "reference_url": ext_ref["plume_surface_interaction_metzger2011"]["url"],
            "published_reference_value": "Apollo/Surveyor annular scour = 1.0–8.0 cm; ejecta sheet angle = 1.0°–3.5°",
            "model_computed_value": f"Scour depth = {scour_depth_cm} cm; ejecta sheet angle = {ejecta_sheet_elevation_deg}°",
            "agreement_status": "screening_consistency_only_not_independent_validation" if 0.5 <= scour_depth_cm <= 8.5 else "caution",
        },
        {
            "domain": "NASA DSN 34m BWG X-Band Free-Space Path Loss (8.42 GHz)",
            "external_source": ext_ref["dsn_34m_bwg_xband_link"]["citation"],
            "reference_url": ext_ref["dsn_34m_bwg_xband_link"]["url"],
            "published_reference_value": f"FSPL = {ext_ref['dsn_34m_bwg_xband_link']['expected_fspl_db']} dB at 384,400 km",
            "model_computed_value": f"FSPL = {fspl_x_db} dB; Eb/N0 Margin = +{link_margin_when_los_clear_db} dB",
            "agreement_status": "screening_consistency_only_not_independent_validation" if abs(fspl_x_db - ext_ref["dsn_34m_bwg_xband_link"]["expected_fspl_db"]) <= 0.1 else "caution",
        },
    ]

    return {
        "service": "landing_site_risk_and_rf_assessment",
        "mode": "evaluated_engineering_model",
        "status": "evaluated",
        "blocked_components": 0,
        "site_id": site_id,
        "site_name": profile["site_name"],
        "lat_deg": lat,
        "lon_deg": lon,
        "provenance_tier": ("real_lola_dem_plus_published_lunar_engineering_models" if site_dem_covered else "curated_regional_fallback_plus_published_lunar_engineering_models"),
        "resolution_and_certification_boundary": resolution_boundary,
        "dem_coverage": {"covered": site_dem_covered, "label": f"{verified_dem.meta.get('product_id')} ({dem_res:g} m/px)" if site_dem_covered else "regional DEM unavailable at requested point", "warning": None if site_dem_covered else "Requested site/pad is outside verified DEM coverage or has NoData; fallback values are screening proxies, not site-specific DEM measurements."},
        "pad_scale_topography": {
            **pad_topo,
            "source": pad_source,
            "source_category": "REAL_DEM_NATIVE_SCALE_GRADIENT" if pad_source == "real_lola_dem_bidirectional_gradient" else "REFERENCE_PROFILE_SCREENING_ONLY",
            "source_badge": pad_source_badge,
            "limitation_badge": "الميل عند دقة DEM الأصلية فقط؛ لا يوجد استقراء Hurst أو اعتماد لهبوط منصة 15م",
            "lander_max_tilt_limit_deg": lander_max_tilt_deg,
            "tilt_margin_deg": tilt_margin_deg,
            "status": slope_status,
        },
        "components": {
            "boulder_hazard": {
                "status": boulder_status,
                "source_category": "PUBLISHED_EMPIRICAL_DISTRIBUTION_AND_ENGINEERING_ASSUMPTION",
                "source_badge": "[Curated Assumption] site rock fraction (not extracted from Diviner) + assumed vehicle clearance (0.65m)",
                "limitation_badge": "تقدير احتمالي إقليمي؛ لا يحدد مواقع الصخور الفردية دون صور LROC NAC (0.5m/px)",
                "source_model": "Curated per-site rock fraction; contextual range only: Bandfield et al. (2011); Surveyor/NAC morphology model",
                "rock_abundance_fraction": profile["rock_abundance_fraction"],
                "rock_abundance_label": "[Curated Assumption] Not extracted from site-specific Diviner data.",
                "rock_abundance_citation": _load_external_benchmarks()["benchmarks"]["boulder_morphometry_and_diviner_ra"]["citation"],
                "boulder_d99_diameter_m": d99_m,
                "boulder_h99_height_m": h99_m,
                "lander_belly_clearance_m": lander_belly_clearance_m,
                "effective_clearance_after_stroke_m": effective_clearance_m,
                "under_deck_clearance_margin_m": boulder_clearance_margin_m,
                "clean_25m_pad_probability_pct": prob_clean_pad_pct,
                "regional_prior_not_a_local_map": True,
                "evidence_tier": "local_LROC_inventory_required",
            },
            "regolith_bearing": {
                "status": regolith_status,
                "source_category": "PUBLISHED_GEOTECHNICAL_MODEL_AND_LANDER_ASSUMPTION",
                "source_badge": "معادلة Terzaghi المرجعية (Lunar Sourcebook) + افتراض كتلة مركبة (1850 kg)",
                "limitation_badge": "نموذج جيوتكنيكي إقليمي؛ يتطلب فحص اختراق مخروطي (CPT) موضعي لاعتماد الهبوط",
                "source_model": "Lunar Sourcebook Highland/Polar Regolith Terzaghi Bearing Model (Carrier et al., 1991)",
                "bulk_density_kg_m3": rho,
                "cohesion_kpa": c_kpa,
                "internal_friction_angle_deg": phi_deg,
                "terzaghi_factors": tf,
                "ultimate_bearing_capacity_kpa": q_ult_kpa,
                "dynamic_touchdown_contact_pressure_kpa": q_contact_kpa,
                "bearing_safety_factor": bearing_safety_factor,
                "estimated_footpad_sinkage_cm": estimated_sinkage_cm,
            },
            "plume_surface_interaction": {
                "status": psi_status,
                "source_category": "PUBLISHED_EROSION_SCALING_AND_ENGINE_ASSUMPTION",
                "source_badge": "نموذج تعرية الغاز (Metzger et al., 2011) + افتراض دفع محرك (15 kN)",
                "limitation_badge": "تقدير تحليلي أحادي البعد؛ لا يحاكي CFD ثلاثي الأبعاد لتفاعل العادم مع تضاريس الفوهة",
                "source_model": "Roberts-Continuum / Metzger et al. (2011) Supersonic Exhaust Ejecta Scour Model",
                "descent_thrust_n": descent_thrust_n,
                "nozzle_cutoff_height_m": nozzle_cutoff_height_m,
                "impingement_wall_shear_pa": wall_shear_stress_pa,
                "critical_regolith_erosion_shear_pa": critical_erosion_shear_pa,
                "predicted_scour_depth_cm": scour_depth_cm,
                "ejecta_sheet_angle_deg": ejecta_sheet_elevation_deg,
                "transient_dust_optical_depth": transient_dust_optical_depth,
            },
            "rf_link_budget": {
                "status": rf_status,
                "source_category": "ANALYTICAL_FRIIS_LINK_BUDGET_AND_HORIZONS_LOS",
                "source_badge": "معادلة Friis القياسية (NASA DSN 810-005) + خط رؤية JPL Horizons/DEM",
                "limitation_badge": "ميزانية رابط اسمية بالفضاء الحر؛ لا تشمل جدولة هوائيات DSN أو التضائل الجوي الأرضي",
                "source_model": "NASA DSN 34m BWG X-Band (8.42 GHz) Surface-to-Earth Link Budget",
                "frequency_ghz": 8.42,
                "range_km": 384400.0,
                "free_space_path_loss_db": fspl_x_db,
                "tx_power_w": rf_tx_power_w,
                "hga_diameter_m": rf_antenna_diam_m,
                "tx_gain_dbi": tx_gain_dbi,
                "eirp_dbw": eirp_dbw,
                "dsn_34m_gt_db_k": dsn_34m_gt_db_k,
                "data_rate_mbps": rf_data_rate_mbps,
                "eb_n0_received_db": eb_n0_received_db,
                "eb_n0_required_ldpc_db": eb_n0_required_ldpc_db,
                "rf_link_margin_when_los_clear_db": link_margin_when_los_clear_db,
                "geometric_dte_los_clear_in_nov2026_window": geometric_los_clear,
                "relay_recommendation": (
                    "Direct-to-Earth X-band link closes with +"
                    + f"{link_margin_when_los_clear_db:.1f} dB margin whenever Earth is above the terrain horizon; "
                    + (
                        "in the Nov 2026 Horizons window at this site, Earth is below the horizon so lunar orbital relay (e.g. Lunar Gateway / Queqiao-2 / CLPS relay) is required."
                        if not geometric_los_clear
                        else "favorable near-side latitude provides Direct-to-Earth geometric visibility."
                    )
                ),
            },
        },
        "independent_literature_validation": independent_validation,
        "literature_validation_note": "These are model-consistency comparisons, not independent site validation or field certification.",
        "scientific_disclaimers": [
            f"DEM-derived gradients are reported at native source resolution ({dem_res:g} m/px). No Hurst extrapolation is used to claim a 15 m pad measurement; the local Site01 tile is not activated where its elevation disagrees with the regional DEM.",
            "[Curated Assumption] Rock abundance and regolith parameters are regional priors, not site measurements. No clean-pad probability is reported without a georeferenced local LROC boulder inventory; field and engineering certification remain unavailable.",
        ],
    }
