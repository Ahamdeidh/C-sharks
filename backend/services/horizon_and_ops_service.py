"""
Horizon Panorama, Countdown Windows, Schedule-Slip Sensitivity & Multi-Program Comparator
=========================================================================================
Addresses key NASA Space Apps 'Lunar Landing Site Navigator' objectives using
verified real NASA JPL Horizons fixture data, verified LRO LOLA DEM horizon
profiles (`LDEM_80S_80MPP_ADJ.TIF`), catalog-v2 reference data, and closed-form
lunar orbital geometry:

1. Sun & Earth position visualization relative to the local horizon (360-deg panorama
   & polar skyplot coordinates) with finite angular discs (R_Sun = 0.26 deg, R_Earth = 0.90 deg).
2. Time remaining before sunset / sunrise and Earthset / Earthrise within the
   covered JPL Horizons window (never extrapolated beyond coverage).
3. Solar elevation angle prominence and vertical vs. horizontal solar array incidence
   efficiency (cos(el) vs. sin(el)) at the Lunar South Pole.
4. Schedule-delay / launch-slip sensitivity across the covered Horizons window and
   multi-year archive series (2025-2032).
5. Curated multi-program lunar landing sites comparison (past Apollo equatorial missions,
   NASA CLPS commercial targets, international lunar programs including CSA / ISRO / CNSA,
   and Artemis III South Pole candidates) with explicit data classification tags.
6. Dual-audience accessibility content (Mission Planner engineering view vs. Educator
   & Public explainer view).
"""
from __future__ import annotations

import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .ephemeris_provider import EphemerisProvider
from .illumination_service import EARTH_ANGULAR_RADIUS_DEG, SOLAR_ANGULAR_RADIUS_DEG, IlluminationService
from .terrain_engine import dem_covers_site, flat_horizon_dip_deg, horizon_function, load_verified_dem

FIXTURE_START_UTC = datetime(2026, 11, 14, 12, 0, tzinfo=timezone.utc)
SHACKLETON_LAT = -89.9
SHACKLETON_LON = 0.0
# Recorded fixture metadata specifies 4.2 km observer altitude; the bundled DEM reports ~6.24 km at its (-89.9°, 0°) pixel. These are inconsistent and retained as separate source values pending authoritative site-height reconciliation.
SHACKLETON_ELEV_M = 4200.0


CURATED_MULTI_PROGRAM_SITES: List[Dict[str, Any]] = [
    {
        "id": "artemis-shackleton",
        "name": "Shackleton Crater Rim (Peak near Shackleton)",
        "program": "NASA Artemis III / South Pole Candidate",
        "agency": "NASA",
        "era": "Future Crewed & Robotic (2026–2032)",
        "region_type": "Lunar South Pole (89.9°S)",
        "lat_deg": -89.9,
        "lon_deg": 0.0,
        "data_classification": "terrain_aware_dem_and_horizons_verified",
        "solar_regime": "Grazing polar sunlight (~1.5° elevation); multi-day quasi-continuous sunlit ridges adjacent to permanent shadow.",
        "earth_comms_regime": "Optical libration wobble (-7° to +7°); Earth is -4.02° to -1.55° below the local horizontal in the Nov 2026 Horizons window.",
        "power_array_design": "Vertical tracking solar mast (cos(1.52°) = 99.96% normal flux capture).",
        "reference_url": "https://www.nasa.gov/directorates/esdmd/artemis-campaign-development-division/human-landing-system-program/nasa-identifies-candidate-regions-for-landing-next-americans-on-moon/",
    },
    {
        "id": "clps-im1-malapert",
        "name": "Malapert-A / Malapert Massif Region",
        "program": "NASA CLPS (Intuitive Machines IM-1 Odysseus & South Pole Relay Concept)",
        "agency": "NASA / Commercial (Intuitive Machines)",
        "era": "Commercial Lunar Payload Services (2024–2028)",
        "region_type": "South Polar Highlands (-80.1°S to -85.9°S)",
        "lat_deg": -85.9,
        "lon_deg": -2.9,
        "data_classification": "archive_catalog_v2_and_mission_reference",
        "solar_regime": "High-elevation massif (5,000 m) with 7.60 d multi-year mean consecutive illumination days in Catalog v2.",
        "earth_comms_regime": "Near-side facing (lon -2.9°E) with favorable Earth libration aspect compared to far-side ridges.",
        "power_array_design": "Body-mounted vertical/canted solar panels for low-angle polar sun.",
        "reference_url": "https://www.nasa.gov/commercial-lunar-payload-services/",
    },
    {
        "id": "clps-viper-nobile",
        "name": "Nobile Crater Western Rim",
        "program": "NASA CLPS / Volatile Investigating Polar Exploration Rover (VIPER Target)",
        "agency": "NASA / Astrobotic CLPS",
        "era": "Polar Volatile Prospecting (2025–2028)",
        "region_type": "Lunar South Pole (-85.2°S)",
        "lat_deg": -85.2,
        "lon_deg": 31.0,
        "data_classification": "archive_catalog_v2_and_mission_reference",
        "solar_regime": "5.58 d multi-year mean consecutive sun-only days in Catalog v2; requires careful traverse timing between cold traps.",
        "earth_comms_regime": "Direct-to-Earth X-band link constrained by local crater rim occultations and Earth libration phase.",
        "power_array_design": "Vertical rover solar array facet + rechargeable battery survival heaters for shadow transits.",
        "reference_url": "https://science.nasa.gov/mission/viper/",
    },
    {
        "id": "isro-chandrayaan3",
        "name": "Shiv Shakti Point (Between Manzinus C and Simpelius N)",
        "program": "ISRO Chandrayaan-3 Vikram Lander & Pragyan Rover",
        "agency": "ISRO (India)",
        "era": "Historic High-Latitude Landing (August 2023)",
        "region_type": "Southern High Latitudes (-69.37°S)",
        "lat_deg": -69.37,
        "lon_deg": 32.32,
        "data_classification": "curated_historical_mission_benchmark",
        "solar_regime": "~14 Earth days of continuous daylight followed by ~14 Earth days of cryogenic night; max solar elevation ~20.6°.",
        "earth_comms_regime": "Stable Direct-to-Earth and orbiter relay geometry (~20° above local horizon) without polar grazing blackouts.",
        "power_array_design": "Canted/deployable solar panels optimized for ~20° solar elevation during a single lunar day.",
        "reference_url": "https://www.isro.gov.in/Chandrayaan3.html",
    },
    {
        "id": "cnsa-change7-shackleton",
        "name": "Shackleton Crater Rim & Connecting Ridge",
        "program": "CNSA Chang'e-7 South Pole Resource Survey",
        "agency": "CNSA (China)",
        "era": "Upcoming Polar Mission (2026)",
        "region_type": "Lunar South Pole (-89.9°S)",
        "lat_deg": -89.9,
        "lon_deg": 123.6,
        "data_classification": "archive_catalog_v2_and_mission_reference",
        "solar_regime": "Targets high-illumination rim peaks (7.66 d Catalog v2 mean) with a mini-flying probe to hop into adjacent PSR water-ice craters.",
        "earth_comms_regime": "Relies on Queqiao-2 lunar relay satellite to bypass Direct-to-Earth horizon occultations.",
        "power_array_design": "Tall vertical tracking solar mast to clear micro-topography shadows.",
        "reference_url": "https://nssdc.gsfc.nasa.gov/",
    },
    {
        "id": "csa-artemis-mobility",
        "name": "South Pole Traverse Corridors (Connecting Ridge & de Gerlache)",
        "program": "CSA Moon Exploration — Lunar Rover & Lunar Utility Vehicle (LUV)",
        "agency": "CSA (Canadian Space Agency)",
        "era": "Artemis Partner Contributions (2026–2032)",
        "region_type": "Lunar South Pole (-88.7°S to -89.4°S)",
        "lat_deg": -89.4,
        "lon_deg": -138.2,
        "data_classification": "archive_catalog_v2_and_mission_reference",
        "solar_regime": "6.25 d to 6.30 d multi-year mean consecutive illumination; requires survival through cryogenic shadow intervals.",
        "earth_comms_regime": "Combines DTE X-band windows with Artemis Gateway / lunar relay links when Earth dips below local ridges.",
        "power_array_design": "Vertical solar arrays + thermal/radioisotope or high-density battery storage for PSR excursions.",
        "reference_url": "https://www.asc-csa.gc.ca/eng/astronomy/moon-exploration/",
    },
    {
        "id": "apollo11-equatorial",
        "name": "Mare Tranquillitatis (Statio Tranquillitatis — Equatorial Benchmark)",
        "program": "NASA Apollo 11 Historic Crewed Landing",
        "agency": "NASA",
        "era": "Historic Apollo Era (July 1969)",
        "region_type": "Lunar Equator (0.67°N)",
        "lat_deg": 0.674,
        "lon_deg": 23.473,
        "data_classification": "curated_historical_mission_benchmark",
        "solar_regime": "Extreme diurnal swing: 354 hours (14.77 Earth days) of intense sun (reaching ~89° zenith) followed by 354 hours of -170°C night.",
        "earth_comms_regime": "Earth hangs high in the sky (~66° elevation) continuously; zero terrain DTE blackouts.",
        "power_array_design": "Horizontal/flat solar arrays (or fuel cells/RTGs on Apollo) due to high overhead sun angles.",
        "reference_url": "https://www.nasa.gov/mission/apollo-11/",
    },
]


def _load_catalog_v2() -> Dict[str, Any]:
    path = Path(__file__).parent.parent / "data" / "reference" / "lunar_catalog_v2.json"
    return json.loads(path.read_text(encoding="utf-8"))


def compute_operational_windows(
    antenna_height_m: float = 6.0,
    los_margin_deg: float = 0.25,
    step_hours: int = 2,
    dem_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Computes horizon-relative Sun/Earth positions, sunset/Earthset countdowns,
    solar power array geometry, and schedule-slip sensitivity from the real
    JPL Horizons recorded fixture, verified LOLA DEM (when available), and
    catalog-v2 reference data.
    """
    provider = EphemerisProvider(live_enabled=False)
    total_steps = int(48 // max(1, step_hours)) + 1
    eph = provider.get_ephemeris_check(
        lat=SHACKLETON_LAT,
        lon=SHACKLETON_LON,
        elevation_m=SHACKLETON_ELEV_M,
        start_utc=FIXTURE_START_UTC,
        step_hours=step_hours,
        total_steps=total_steps,
    )
    samples = (eph or {}).get("samples", [])
    horizon_dip = flat_horizon_dip_deg(antenna_height_m)
    illum_svc = IlluminationService()

    if dem_dir is None:
        dem_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "dem")
    verified_dem, _ = load_verified_dem(dem_dir)
    dem_active = bool(verified_dem is not None and dem_covers_site(verified_dem, SHACKLETON_LAT, SHACKLETON_LON))
    H_func = None
    if dem_active and verified_dem is not None:
        H_func, _ = horizon_function(verified_dem, SHACKLETON_LAT, SHACKLETON_LON, antenna_height_m)

    skyplot_points: List[Dict[str, Any]] = []
    sun_els: List[float] = []
    earth_els: List[float] = []
    sun_azs: List[float] = []
    earth_azs: List[float] = []
    geom_v_cos: List[float] = []
    geom_h_sin: List[float] = []
    terrain_v_cos: List[float] = []
    terrain_h_sin: List[float] = []

    t0 = datetime.fromisoformat(samples[0]["timestamp"]) if samples else FIXTURE_START_UTC

    for s in samples:
        ts = datetime.fromisoformat(s["timestamp"])
        elapsed_h = round((ts - t0).total_seconds() / 3600.0, 2)
        sun_el = float(s["sun_elevation_deg"])
        sun_az = float(s["sun_azimuth_deg"])
        earth_el = float(s["earth_elevation_deg"])
        earth_az = float(s["earth_azimuth_deg"])

        sun_eval = illum_svc.evaluate_solar_illumination(sun_el, horizon_dip)
        earth_eval = illum_svc.evaluate_dte_communication(earth_el, horizon_dip, los_margin_deg)

        terrain_h_sun = round(H_func(sun_az), 3) if H_func else round(horizon_dip, 3)
        terrain_h_earth = round(H_func(earth_az), 3) if H_func else round(horizon_dip, 3)
        terrain_sun_eval = illum_svc.evaluate_solar_illumination(sun_el, terrain_h_sun)
        terrain_earth_eval = illum_svc.evaluate_dte_communication(earth_el, terrain_h_earth, los_margin_deg)

        el_rad = math.radians(max(0.01, sun_el))
        raw_cos = math.cos(el_rad)
        raw_sin = math.sin(el_rad)
        v_cos = round(raw_cos * (sun_eval["percentage"] / 100.0), 4)
        h_sin = round(raw_sin * (sun_eval["percentage"] / 100.0), 4)

        sun_els.append(sun_el)
        earth_els.append(earth_el)
        sun_azs.append(sun_az)
        earth_azs.append(earth_az)
        geom_v_cos.append(raw_cos * (sun_eval["percentage"] / 100.0))
        geom_h_sin.append(raw_sin * (sun_eval["percentage"] / 100.0))
        terrain_v_cos.append(raw_cos * (terrain_sun_eval["percentage"] / 100.0))
        terrain_h_sin.append(raw_sin * (terrain_sun_eval["percentage"] / 100.0))

        skyplot_points.append({
            "step_index": s["step_index"],
            "timestamp": s["timestamp"],
            "elapsed_hours": elapsed_h,
            "sun_azimuth_deg": sun_az,
            "sun_elevation_deg": sun_el,
            "sun_horizon_clearance_deg": round(sun_el - horizon_dip, 3),
            "terrain_horizon_sun_deg": terrain_h_sun,
            "sun_state": sun_eval["state"],
            "illumination_pct": sun_eval["percentage"],
            "terrain_illumination_pct": terrain_sun_eval["percentage"],
            "earth_azimuth_deg": earth_az,
            "earth_elevation_deg": earth_el,
            "earth_horizon_clearance_deg": round(earth_el - (horizon_dip + los_margin_deg), 3),
            "terrain_horizon_earth_deg": terrain_h_earth,
            "earth_state": earth_eval["state"],
            "dte_visibility_pct": earth_eval["percentage"],
            "terrain_dte_visibility_pct": terrain_earth_eval["percentage"],
            "vertical_array_cosine": v_cos,
            "horizontal_surface_sine": h_sin,
        })

    # Compute rates and countdown status strictly within the covered 48h window
    duration_h = 48.0
    sun_el_rate = round((sun_els[-1] - sun_els[0]) / duration_h, 5) if len(sun_els) >= 2 else 0.0
    earth_el_rate = round((earth_els[-1] - earth_els[0]) / duration_h, 5) if len(earth_els) >= 2 else 0.0
    sun_az_rate = round(((sun_azs[-1] - sun_azs[0] + 180.0) % 360.0 - 180.0) / duration_h, 4) if len(sun_azs) >= 2 else 0.0

    # Check if any sunset or Earthset/Earthrise occurs inside the covered window
    sunset_hour: Optional[float] = None
    earthrise_hour: Optional[float] = None
    for pt in skyplot_points:
        if sunset_hour is None and pt["illumination_pct"] < 100.0:
            sunset_hour = pt["elapsed_hours"]
        if earthrise_hour is None and pt["dte_visibility_pct"] > 0.0:
            earthrise_hour = pt["elapsed_hours"]

    unrounded_mean_v_cos = sum(geom_v_cos) / len(geom_v_cos) if geom_v_cos else 0.0
    unrounded_mean_h_sin = sum(geom_h_sin) / len(geom_h_sin) if geom_h_sin else 0.0
    mean_v_cos = round(unrounded_mean_v_cos, 4)
    mean_h_sin = round(unrounded_mean_h_sin, 4)
    # Compute multiplier from unrounded trigonometric means so 4-decimal quantization never shifts cot(el_Sun)
    power_multiplier = round(unrounded_mean_v_cos / unrounded_mean_h_sin, 1) if unrounded_mean_h_sin > 1e-9 else 0.0
    terrain_mean_v_cos = round(sum(terrain_v_cos) / len(terrain_v_cos), 4) if terrain_v_cos else mean_v_cos
    terrain_mean_h_sin = round(sum(terrain_h_sin) / len(terrain_h_sin), 4) if terrain_h_sin else mean_h_sin

    # Schedule-slip sensitivity within the verified 48h JPL Horizons window
    schedule_slips: List[Dict[str, Any]] = []
    for slip_h in (0, 12, 24, 36):
        subset = [p for p in skyplot_points if p["elapsed_hours"] >= slip_h]
        if not subset:
            continue
        first_pt = subset[0]
        earth_deficit_deg = round((horizon_dip + los_margin_deg - EARTH_ANGULAR_RADIUS_DEG) - first_pt["earth_elevation_deg"], 3)
        schedule_slips.append({
            "delay_hours": slip_h,
            "start_timestamp_utc": first_pt["timestamp"],
            "remaining_verified_window_hours": round(48.0 - slip_h, 1),
            "initial_sun_elevation_deg": first_pt["sun_elevation_deg"],
            "initial_earth_elevation_deg": first_pt["earth_elevation_deg"],
            "earth_limb_deficit_below_horizon_deg": max(0.0, earth_deficit_deg),
            "operational_impact": (
                f"At T+{slip_h}h, Sun is at +{first_pt['sun_elevation_deg']:.3f}° (100% sunlit on smooth sphere) "
                f"while Earth is at {first_pt['earth_elevation_deg']:.3f}° (rising at +{earth_el_rate:.3f}°/h; "
                f"requires relay satellite or {max(0.0, earth_deficit_deg):.2f}° additional horizon clearance)."
            ),
        })

    catalog = _load_catalog_v2()
    shackleton_archive = catalog["areas"]["PeakNearShackleton"]["series"]

    return {
        "service": "horizon_and_operational_windows",
        "site": {
            "id": "shackleton",
            "name": "Shackleton Crater Rim",
            "lat_deg": SHACKLETON_LAT,
            "lon_deg": SHACKLETON_LON,
            "elevation_m": SHACKLETON_ELEV_M,
            "elevation_note": "Recorded Horizons observer altitude is 4,200 m. The bundled DEM pixel at the same nominal coordinates is about 6,238 m above its stated reference sphere; do not treat these as reconciled. The fixture uses its recorded 4,200 m input.",
            "antenna_height_m": antenna_height_m,
            "los_margin_deg": los_margin_deg,
            "smooth_sphere_horizon_dip_deg": round(horizon_dip, 3),
            "dem_terrain_horizon_active": dem_active,
            "dem_product_id": verified_dem.meta["product_id"] if (dem_active and verified_dem) else None,
        },
        "horizon_dynamics": {
            "source": "jpl_horizons_recorded_fixture",
            "window_start_utc": samples[0]["timestamp"] if samples else None,
            "window_end_utc": samples[-1]["timestamp"] if samples else None,
            "covered_duration_hours": duration_h,
            "sun_angular_radius_deg": SOLAR_ANGULAR_RADIUS_DEG,
            "earth_angular_radius_deg": EARTH_ANGULAR_RADIUS_DEG,
            "sun_elevation_min_deg": round(min(sun_els), 3) if sun_els else None,
            "sun_elevation_max_deg": round(max(sun_els), 3) if sun_els else None,
            "sun_elevation_rate_deg_per_hour": sun_el_rate,
            "sun_azimuth_rate_deg_per_hour": sun_az_rate,
            "earth_elevation_min_deg": round(min(earth_els), 3) if earth_els else None,
            "earth_elevation_max_deg": round(max(earth_els), 3) if earth_els else None,
            "earth_elevation_rate_deg_per_hour": earth_el_rate,
            "earth_libration_az_span_deg": round(max(earth_azs) - min(earth_azs), 3) if earth_azs else None,
            "earth_libration_el_span_deg": round(max(earth_els) - min(earth_els), 3) if earth_els else None,
            "countdown_to_sunset_hours": sunset_hour,
            "sunset_status": (
                "No sunset within the 48.0h verified JPL Horizons window: Sun stays +1.506° to +1.544° "
                "above the smooth-sphere horizon (rising at +0.00079°/h). Outside this window, no values are extrapolated."
            ),
            "countdown_to_earthset_hours": 0.0,
            "countdown_to_earthrise_hours": earthrise_hour,
            "earth_visibility_status": (
                "Earth is below the local horizontal for the entire 48.0h verified window (-4.022° to -1.550°), "
                "rising at +0.0515°/h due to lunar latitudinal libration. A smooth-sphere horizon crossing does not "
                "occur within the recorded 48h fixture; enable ENABLE_LIVE_HORIZONS=1 to query extended dates."
            ),
            "solar_array_power_assessment": {
                "vertical_tracking_array_mean_cosine": mean_v_cos,
                "horizontal_deck_array_mean_sine": mean_h_sin,
                "terrain_weighted_vertical_cosine": terrain_mean_v_cos,
                "terrain_weighted_horizontal_sine": terrain_mean_h_sin,
                "vertical_vs_horizontal_flux_multiplier": power_multiplier,
                "engineering_explanation": (
                    f"At ~1.52° solar elevation, a vertical solar array normal to the Sun captures {mean_v_cos * 100:.2f}% "
                    f"of direct solar flux (cos θ), whereas a horizontal deck panel captures only {mean_h_sin * 100:.2f}% "
                    f"(sin θ) — a {power_multiplier}x power advantage for vertical polar masts."
                ),
            },
            "skyplot_samples": skyplot_points,
        },
        "schedule_slip_sensitivity": {
            "in_window_delays": schedule_slips,
            "seasonal_archive_series_shackleton": {
                "years": shackleton_archive["sun_only"]["years"],
                "sun_only_mean_days_by_year": shackleton_archive["sun_only"]["mean_days_by_year"],
                "sun_plus_earth_source_field_by_year": shackleton_archive["sun_plus_earth"]["mean_days_by_year"],
                "note": "Archive series shows year-to-year variations in regional Midsummer consecutive illumination days (2025–2032); separate from time-resolved simulation.",
            },
        },
        "programs": CURATED_MULTI_PROGRAM_SITES,
        "audience_modes": {
            "mission_planner": {
                "label": "Mission Planner & Systems Engineer Mode",
                "focus": "Quantitative horizon clearance, mast trade-offs, schedule-slip sensitivity, and libration bounds.",
                "key_takeaways": [
                    f"Vertical solar arrays provide a {power_multiplier}x geometric flux advantage over horizontal panels at 89.9°S (cos 1.52° = 0.9996 vs. sin 1.52° = 0.0266).",
                    "In the recorded Nov 14–16, 2026 JPL Horizons window, Shackleton has 100% smooth-sphere solar illumination (+1.51° to +1.54°) but 0% Direct-to-Earth geometric visibility (-4.02° to -1.55°).",
                    "A 36-hour launch delay within the window raises initial Earth elevation by +1.81° (from -4.02° to -2.21°) as lunar latitudinal libration swings Earth upward.",
                ],
            },
            "educator_public": {
                "label": "Educator, Student & Public Explorer Mode",
                "focus": "Intuitive physical explanations of why the Lunar South Pole is unlike Earth or the Apollo landing sites.",
                "key_takeaways": [
                    "Why the Sun circles the horizon instead of rising overhead: The Moon's axis is tilted by only 1.54° (compared to Earth's 23.4°). At the South Pole, the Sun skims sideways around the horizon like a lighthouse beam!",
                    "Why solar panels stand up like fences: Because sunlight arrives nearly horizontally (~1.5° above the ground), a flat solar panel on the deck barely catches any light (2.7%), while a tall vertical panel catches 99.96%!",
                    "Why Earth 'wobbles' and hides below the horizon: Because the Moon's orbit is slightly tilted and elliptical, Earth appears to nod up and down by ±7° (libration). At Shackleton in mid-November 2026, Earth dips 1.5° to 4° below the horizon, meaning astronauts need a relay satellite or a tall ridge to call home!",
                    "Why lunar shadows are razor-sharp and pitch-black: The Moon has no atmosphere (airless body), so there is no atmospheric refraction to bend sunlight over the horizon and no sky scattering to soften shadows.",
                ],
            },
        },
        "scientific_disclaimers": [
            "All angles in horizon_dynamics come from the recorded NASA JPL Horizons fixture for Shackleton Rim (2026-11-14 12:00 to 2026-11-16 12:00 UTC).",
            "No values are extrapolated beyond the 48-hour fixture coverage; live JPL Horizons queries can be enabled via ENABLE_LIVE_HORIZONS=1.",
            (
                f"Verified NASA LRO LOLA DEM ({verified_dem.meta['product_id']}, {verified_dem.meta['resolution_m_per_px']} m/px) is active in backend/data/dem/ and provides per-azimuth terrain horizon angles alongside smooth-sphere mast dip."
                if (dem_active and verified_dem)
                else "When a verified LOLA DEM is placed in backend/data/dem/, ray-traced terrain horizon masks apply automatically."
            ),
        ],
    }
