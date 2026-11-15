"""
Simulation Engine Orchestrator
==============================
Coordinates ephemeris retrieval, reference-frame transformations,
verified LOLA DEM (`LDEM_80S_80MPP_ADJ.TIF`) horizon raytracing,
bidirectional pad-scale slope extraction, integrated landing-risk & RF
link-budget engineering models, and per-metric provenance logging.
"""

import math
import os
import glob
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple, Any

from .horizons_service import HorizonsService
from .spice_service import SpiceKernelStatus, LocalFrameTransform
from .dem_service import DemService, DemMetadata, LUNAR_RADIUS_M
from .ephemeris_provider import EphemerisProvider
from .illumination_service import (
    IlluminationService,
    SOLAR_ANGULAR_RADIUS_DEG,
    EARTH_ANGULAR_RADIUS_DEG
)
from .scientific_validation_service import build_validation_report
from .terrain_engine import (
    compute_bidirectional_pad_metrics,
    compute_reference_kpis,
    compute_terrain_aware,
    dem_covers_site,
    load_verified_dem,
    site_pixel,
)
from .landing_risk_service import evaluate_landing_site_risk

PREDEFINED_SITES = [
  {
    "id": "shackleton",
    "name": "Shackleton Crater Rim",
    "lat": -89.9,
    "lon": 0.0,
    "elevation_m": 4200.0,
    "description": "Connecting ridge adjacent to Shackleton crater; peak experiences high annual solar illumination.",
    "is_illustrative": True,
    "estimates_classification": "illustrative_preset_baseline_not_certified",
    "source_badge": "ملف مرجعي تمهيدي (Illustrative Preset Baseline)",
    "limitation_badge": "قيم البطاقة التمهيدية للفرز الأولي فقط؛ اضغط Run Simulation لحساب DEM 80m + JPL Horizons الفعلي",
    "base_illum_estimate": 86.4,
    "base_dte_estimate": 74.2,
    "slope_avg_deg": 6.4,
    "max_amsi": "0.12 (Low)",
    "avg_asia_hours": 14.2,
    "baseline_score": 4.9,
    "tradeoffs": {
      "advantages": [
        "[Illustrative Preset Estimate] High annual polar ridge illumination; run simulation for time-resolved LOLA DEM + JPL Horizons calculation",
        "Direct visibility to polar orbiting lunar relays"
      ],
      "downsides": [
        "Steep inner crater walls (>25°) present severe tip-over hazard outside rim crest",
        "Narrow ridge width (<100m) constrains landing footprint"
      ],
      "data_quality_note": "Preset summary figures (base_illum_estimate, base_dte_estimate, baseline_score) are illustrative triage references only; verified LOLA DEM (LDEM_80S_80MPP_ADJ.TIF) ray-tracing is used during simulation execution."
    }
  },
  {
    "id": "malapert",
    "name": "Malapert Massif Ridge",
    "lat": -85.9,
    "lon": -2.9,
    "elevation_m": 5000.0,
    "description": "Elevated massif with favorable near-side Earth visibility and elevated solar clearance.",
    "is_illustrative": True,
    "estimates_classification": "illustrative_preset_baseline_not_certified",
    "source_badge": "ملف مرجعي تمهيدي (Illustrative Preset Baseline)",
    "limitation_badge": "قيم البطاقة التمهيدية للفرز الأولي فقط؛ تتطلب ENABLE_LIVE_HORIZONS=1 للحساب اللحظي عند -85.9°S",
    "base_illum_estimate": 89.1,
    "base_dte_estimate": 88.5,
    "slope_avg_deg": 4.8,
    "max_amsi": "0.08 (Very Low)",
    "avg_asia_hours": 8.5,
    "baseline_score": 5.0,
    "tradeoffs": {
      "advantages": [
        "[Illustrative Preset Estimate] Favorable near-side communications aspect (-2.9°E)",
        "Broad, relatively flat plateau crest suitable for landing gear stability"
      ],
      "downsides": [
        "Lower latitude (-85.9°S) causes seasonal solar dip during southern lunar winter",
        "Higher transit delta-v from polar orbit compared to 89°S sites"
      ],
      "data_quality_note": "Preset summary figures are illustrative triage references only; live JPL Horizons ephemeris is required for time-resolved simulation at -85.9°S."
    }
  },
  {
    "id": "connecting-ridge",
    "name": "Connecting Ridge",
    "lat": -89.4,
    "lon": 222.0,
    "elevation_m": 3800.0,
    "description": "Narrow topographical ridge between de Gerlache and Shackleton craters.",
    "is_illustrative": True,
    "estimates_classification": "illustrative_preset_baseline_not_certified",
    "source_badge": "ملف مرجعي تمهيدي (Illustrative Preset Baseline)",
    "limitation_badge": "قيم البطاقة التمهيدية للفرز الأولي فقط؛ ليست اعتماد هبوط تشغيلي",
    "base_illum_estimate": 82.3,
    "base_dte_estimate": 68.0,
    "slope_avg_deg": 8.1,
    "max_amsi": "0.18 (Moderate)",
    "avg_asia_hours": 18.4,
    "baseline_score": 4.6,
    "tradeoffs": {
      "advantages": [
        "[Illustrative Preset Estimate] Traversable saddle corridor connecting Shackleton and de Gerlache craters",
        "Moderate illumination (~82% illustrative baseline) with multiple local sunlit knolls"
      ],
      "downsides": [
        "Intermittent geometric Earth occultations behind high massifs",
        "Canyon-like shadow casting during low solar elevation angles"
      ],
      "data_quality_note": "Preset summary figures are illustrative triage references only; LOLA DEM (LDEM_80S_80MPP_ADJ.TIF) covers this site and awaits ephemeris window coverage."
    }
  },
  {
    "id": "de-gerlache",
    "name": "de Gerlache Rim 1",
    "lat": -88.5,
    "lon": -88.3,
    "elevation_m": 3100.0,
    "description": "Northwest crater rim featuring moderate elevation and proximity to permanently shadowed water ice candidates.",
    "is_illustrative": True,
    "estimates_classification": "illustrative_preset_baseline_not_certified",
    "source_badge": "ملف مرجعي تمهيدي (Illustrative Preset Baseline)",
    "limitation_badge": "قيم البطاقة التمهيدية للفرز الأولي فقط؛ ليست اعتماد هبوط تشغيلي",
    "base_illum_estimate": 78.5,
    "base_dte_estimate": 61.2,
    "slope_avg_deg": 9.2,
    "max_amsi": "0.22 (Moderate)",
    "avg_asia_hours": 21.0,
    "baseline_score": 4.4,
    "tradeoffs": {
      "advantages": [
        "[Illustrative Preset Estimate] Immediate proximity to permanently shadowed cold traps with volatile deposits",
        "High-priority scientific sampling destination for in-situ resource utilization (ISRU)"
      ],
      "downsides": [
        "Extended continuous darkness stretches (up to ~21h illustrative baseline)",
        "Low Earth elevation angles require antenna mast >10m or lunar relay for line-of-sight clearance"
      ],
      "data_quality_note": "Preset summary figures are illustrative triage references only; not a certified time-resolved terrain result."
    }
  },
  {
    "id": "haworth",
    "name": "Haworth Crater Rim",
    "lat": -87.4,
    "lon": -5.1,
    "elevation_m": 2400.0,
    "description": "Crater rim situated near deep cold traps; lower elevation requires taller antenna masts for line-of-sight.",
    "is_illustrative": True,
    "estimates_classification": "illustrative_preset_baseline_not_certified",
    "source_badge": "ملف مرجعي تمهيدي (Illustrative Preset Baseline)",
    "limitation_badge": "قيم البطاقة التمهيدية للفرز الأولي فقط؛ ليست اعتماد هبوط تشغيلي",
    "base_illum_estimate": 74.0,
    "base_dte_estimate": 57.8,
    "slope_avg_deg": 11.5,
    "max_amsi": "0.29 (High PSR)",
    "avg_asia_hours": 26.8,
    "baseline_score": 4.1,
    "tradeoffs": {
      "advantages": [
        "[Illustrative Preset Estimate] Direct rim access to one of the coldest known PSR thermal environments on the Moon",
        "Rich scientific target for pristine cryogenic regolith preservation"
      ],
      "downsides": [
        "Lowest elevation (2,400m) among candidate sites increases terrain horizon blockage",
        "Lower Earth geometric line-of-sight availability creates communication blackouts"
      ],
      "data_quality_note": "Preset summary figures are illustrative triage references only; see landing_risk_assessment for physics-based pad-scale and RF screening."
    }
  }
]


KPI_PROVENANCE_LABELS: Dict[str, Dict[str, str]] = {
    "avg_illumination_pct": {
        "source_type": "REAL_LOLA_DEM_AND_JPL_HORIZONS",
        "source_label": "ناتج عن DEM فعلي (LDEM_80S_80MPP_ADJ 80m/px) + زوايا JPL Horizons الحقيقية",
        "limitation": "يحسب حجب الأفق الإقليمي (≥80م) وقرص الشمس المحدود (0.26°)؛ لا يمثل الصخور المحلية (<80م) أو نوافذ خريطة الـ 60 يوماً خارج تغطية Horizons.",
    },
    "dte_connection_pct": {
        "source_type": "REAL_LOLA_DEM_AND_JPL_HORIZONS",
        "source_label": "ناتج عن DEM فعلي (80m/px) + زوايا الأرض من JPL Horizons",
        "limitation": "رؤية هندسية خطية (Geometric LOS) فقط؛ ميزانية الترددات الراديوية (8.42 GHz X-Band) تُعرض منفصلة في لوحة المخاطر الهندسية.",
    },
    "longest_continuous_darkness_hours": {
        "source_type": "REAL_LOLA_DEM_AND_JPL_HORIZONS",
        "source_label": "ناتج عن DEM فعلي (80m/px) + السلسلة الزمنية الموثقة لـ JPL Horizons",
        "limitation": "محسوب ضمن نافذة التغطية الفلكية الموثقة دون أي استقراء زمني خارجها.",
    },
    "longest_earth_blackout_hours": {
        "source_type": "REAL_LOLA_DEM_AND_JPL_HORIZONS",
        "source_label": "ناتج عن DEM فعلي (80m/px) + السلسلة الزمنية الموثقة لـ JPL Horizons",
        "limitation": "محسوب ضمن نافذة التغطية الفلكية الموثقة؛ يتطلب قمراً صناعياً للترحيل (Lunar Relay) عند كون الأرض تحت الأفق.",
    },
    "slope_avg_deg": {
        "source_type": "REAL_LOLA_DEM_BIDIRECTIONAL_GRADIENT",
        "source_label": "ناتج عن اشتقاق ثنائي الاتجاه (شرق-غرب / شمال-جنوب) من DEM فعلي بدقة 80م/بكسل",
        "limitation": "تُعرض الميول عند دقة المصدر فقط؛ لا يُستقرأ ميل منصة 15م من البكسلات الإقليمية ولا يغني عن مسح LROC NAC موضعي.",
    },
    "composite_score": {
        "source_type": "ENGINEERING_TRIAGE_ASSUMPTION",
        "source_label": "افتراض هندسي للفرز الأولي (Design Triage Index) وليس معياراً رسمياً من NASA",
        "limitation": "مؤشر مقارنة تمهيدي بأوزان افتراضية؛ لا يُستخدم كشهادة صلاحية أو اعتماد نهائي لموقع الهبوط.",
    },
}


class SimulationEngine:
    """Orchestrates simulation execution, provenance tracking, and data integrity."""

    def __init__(self, dem_dir: Optional[str] = None):
        self.horizons_svc = HorizonsService()
        self.spice_status = SpiceKernelStatus()
        self.dem_svc = DemService(dem_dir)
        self._dem_cache: Dict[str, Any] = {}
        self.illum_svc = IlluminationService()
        self.ephemeris = EphemerisProvider(horizons=self.horizons_svc)

    def get_full_provenance(self) -> Dict[str, Any]:
        """Assembles official source provenance, URLs, versions, and methodology."""
        dem_avail = self.dem_svc.check_local_dem_availability()
        kernel_avail = self.spice_status.evaluate_kernel_coverage()
        verified_dem, dem_report = self._verified_dem()

        dem_status_str = (
            f"Active & Verified: {verified_dem.meta['product_id']} ({verified_dem.meta['resolution_m_per_px']} m/px Polar Stereographic GeoTIFF, shape {list(verified_dem.raster.shape)}) connected to runtime horizon ray-tracing and bidirectional pad-scale slope extraction."
            if verified_dem is not None
            else "Format specification verified; no verified GeoTIFF currently loaded in dem_dir."
        )

        return {
            "official_sources": [
                {
                    "name": "JPL Solar System Dynamics (Horizons API)",
                    "url": "https://ssd.jpl.nasa.gov/api/horizons.api",
                    "documentation": "https://ssd-api.jpl.nasa.gov/doc/horizons.html",
                    "role": "Ephemeris vectors for Sun ('10') and Earth ('399') apparent elevation/azimuth in lunar topocentric frame.",
                    "status": "Active: Drives ephemeris_check, reference_kpis, horizon-ops, and terrain_aware illumination/DTE (live query when ENABLE_LIVE_HORIZONS=1, otherwise recorded Shackleton fixture 2026-11-14 to 2026-11-16 UTC)."
                },
                {
                    "name": "USGS Astrogeology PDS Geosciences Node (Orbital Data Explorer - ODE) / NASA LRO LOLA",
                    "url": "https://ode.rsl.wustl.edu/",
                    "product_id": verified_dem.meta["product_id"] if verified_dem else "LRO-L-LOLA-4-GDR-V1.0 (LDEM_80S_80MPP_ADJ)",
                    "role": "Digital Elevation Model rasters for lunar south pole topography, 360-deg horizon ray-tracing, geodetic control verification, and bidirectional pad-scale slope extraction.",
                    "status": dem_status_str,
                    "local_files_found": dem_avail["dem_files"],
                    "verification_summary": dem_report,
                },
                {
                    "name": "NAIF SPICE Toolkit & Lunar Kernels",
                    "url": "https://naif.jpl.nasa.gov/naif/data.html",
                    "role": "Frame transformations (ICRF -> MOON_ME -> Topocentric ENU).",
                    "status": "Closed-form topocentric ENU & Polar Stereographic transformations verified against 6 IAU/LOLA control points.",
                    "all_kernels_available": kernel_avail["all_kernels_available"]
                },
                {
                    "name": "NASA Moon Trek & LRO Diviner / Lunar Sourcebook Engineering Baselines",
                    "url": "https://trek.nasa.gov/moon/",
                    "role": "Visual verification context and published lunar highland/polar rock abundance, regolith Terzaghi bearing, plume-surface scouring, and DSN 34m BWG X-band link budget parameters.",
                    "status": "Connected to landing_risk_assessment screening service with independent external literature cross-validation."
                }
            ],
            "methodology": {
                "lunar_reference_radius_m": LUNAR_RADIUS_M,
                "curvature_correction": "Delta_z = r^2 / (2 * R_Moon)",
                "solar_angular_radius_deg": SOLAR_ANGULAR_RADIUS_DEG,
                "earth_angular_radius_deg": EARTH_ANGULAR_RADIUS_DEG,
                "celestial_bodies_treatment": "Finite disc diameter modeled for both Sun (penumbra/umbra) and Earth",
                "antenna_mast_geometry": "Observer vantage point elevated by mast height above ground surface",
                "coordinate_systems": {
                    "inertial": "ICRF (J2000)",
                    "lunar_body_fixed": "MOON_ME (IAU Mean Earth/Polar Axis)",
                    "topocentric": "ENU (East-North-Up local tangent plane)"
                }
            },
            "last_verified_at": datetime.now(timezone.utc).isoformat()
        }

    def _verified_dem(self):
        """Load (and cache by mtime) the configured regional DEM."""
        return load_verified_dem(self.dem_svc.dem_dir)

    def _verified_dem_for_site(self, lat: float, lon: float):
        """Select a user-provided 5 m tile only after footprint and regional-height checks."""
        default_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "dem")
        regional, regional_report = self._verified_dem()
        if os.path.abspath(self.dem_svc.dem_dir) != os.path.abspath(default_dir):
            return regional, {**regional_report, "selection": "explicit_dem_dir"}
        package_dem_root = os.path.join(os.path.dirname(default_dir), "challenge_package", "dem")
        rejected = []
        for tile_dir in sorted(glob.glob(os.path.join(package_dem_root, "Site*"))):
            tile, tile_report = load_verified_dem(tile_dir)
            if tile is None:
                rejected.append({"tile_dir": tile_dir, "reason": "no accepted elevation raster", "report": tile_report})
                continue
            radius = float(tile.meta.get("max_search_radius_m", 1000.0))
            if not dem_covers_site(tile, lat, lon, radius_m=radius):
                continue
            if regional is None or not dem_covers_site(regional, lat, lon, radius_m=800.0):
                rejected.append({"tile_dir": tile_dir, "reason": "regional cross-check unavailable; tile not activated"})
                continue
            tr, tc = site_pixel(tile, lat, lon)
            rr, rc = site_pixel(regional, lat, lon)
            if not (0 <= tr < tile.raster.shape[0] and 0 <= tc < tile.raster.shape[1] and
                    0 <= rr < regional.raster.shape[0] and 0 <= rc < regional.raster.shape[1]):
                rejected.append({"tile_dir": tile_dir, "reason": "cross-check sample outside raster"})
                continue
            tile_z, regional_z = float(tile.raster[tr, tc]), float(regional.raster[rr, rc])
            delta = abs(tile_z - regional_z)
            cross_check = {"tile_elevation_m": round(tile_z, 2), "regional_elevation_m": round(regional_z, 2),
                           "absolute_difference_m": round(delta, 2), "maximum_allowed_difference_m": 100.0,
                           "tile_uncertainty_status": ("provided_in_archive_not_ingested" if tile.meta.get("uncertainty_status") == "provided" else "not_provided"),
                           "uncertainty_layer_ingested": False}
            if tile_z <= -32000 or regional_z <= -32000 or delta > 100.0:
                rejected.append({"tile_dir": tile_dir, "reason": "elevation disagreement exceeds 100 m; possible datum/geolocation mismatch",
                                 "cross_check": cross_check, "report": tile_report})
                continue
            return tile, {**tile_report, "selection": "site_specific_challenge_tile", "challenge_tile_cross_check": cross_check,
                          "uncertainty_layer_ingested": False,
                          "uncertainty_note": "Companion uncertainty rasters are retained but are not ingested into the risk calculation.",
                          "other_challenge_tiles_rejected": rejected}
        result = {**regional_report, "selection": "regional_fallback", "challenge_tile_checks": rejected}
        relevant = next((r for r in rejected if r.get("cross_check")), None)
        if relevant:
            result["challenge_tile_rejection"] = relevant["reason"]
            result["challenge_tile_cross_check"] = relevant["cross_check"]
            result["challenge_tile_report"] = relevant.get("report")
        return regional, result

    def resolve_site_coordinates(self, site_id: str, lat: float, lon: float) -> Tuple[Dict[str, Any], float, float, Optional[str], str]:
        matched = next((s for s in PREDEFINED_SITES if s["id"] == site_id), None)
        if not matched:
            raise ValueError(f"Unknown site_id '{site_id}'. Valid sites: {[s['id'] for s in PREDEFINED_SITES]}")

        mismatch_warning = None
        if abs(lat - matched["lat"]) > 0.01 or abs(lon - matched["lon"]) > 0.01:
            precedence = "custom coordinates override predefined site"
            mismatch_warning = (
                f"Submitted coordinates ({lat}, {lon}) differ from registered site '{matched['name']}' "
                f"({matched['lat']}, {matched['lon']}). Using submitted coordinates per precedence rules."
            )
            eval_lat, eval_lon = lat, lon
        else:
            precedence = "predefined registered site coordinates"
            eval_lat, eval_lon = matched["lat"], matched["lon"]

        return matched, eval_lat, eval_lon, mismatch_warning, precedence

    def run(
        self,
        site_id: str,
        lat: float,
        lon: float,
        start_time_iso: str,
        mission_duration_days: int,
        timestep_hours: int,
        antenna_height_m: float,
        los_margin_deg: float,
        demo_mode: bool = False
    ) -> Dict[str, Any]:
        matched_site, eval_lat, eval_lon, coord_warning, precedence_rule = self.resolve_site_coordinates(site_id, lat, lon)

        start_dt = datetime.fromisoformat(start_time_iso.replace("Z", "+00:00"))
        start_utc = start_dt.astimezone(timezone.utc)

        inputs_echo = {
            "site_id": site_id,
            "site_name": matched_site["name"],
            "lat": eval_lat,
            "lon": eval_lon,
            "elevation_ground_m": matched_site["elevation_m"],
            "start_time_utc": start_utc.isoformat(),
            "start_time_submitted": start_time_iso,
            "mission_duration_days": mission_duration_days,
            "timestep_hours": timestep_hours,
            "antenna_height_m": antenna_height_m,
            "los_margin_deg": los_margin_deg,
            "demo_mode": False,
            "demo_mode_requested": demo_mode,
            "scientific_integrity_policy": "synthetic_demo_disabled",
            "coordinate_precedence": precedence_rule
        }

        provenance = self.get_full_provenance()

        total_hours = mission_duration_days * 24
        total_steps = math.ceil(total_hours / timestep_hours)
        ephemeris_check = self.ephemeris.get_ephemeris_check(
            lat=eval_lat,
            lon=eval_lon,
            elevation_m=matched_site["elevation_m"],
            start_utc=start_utc,
            step_hours=timestep_hours,
            total_steps=total_steps,
        )

        if ephemeris_check and ephemeris_check.get("fixture"):
            fixture_coords = ephemeris_check["fixture"].get("coordinates") or {}
            fixture_alt_m = fixture_coords.get("elevation_km")
            if fixture_alt_m is not None:
                fixture_alt_m = float(fixture_alt_m) * 1000.0
                inputs_echo["ephemeris_observer_elevation_m"] = fixture_alt_m
                if abs(fixture_alt_m - float(matched_site["elevation_m"])) > 100.0:
                    inputs_echo["ephemeris_altitude_mismatch_warning"] = (
                        f"Recorded Horizons observer altitude ({fixture_alt_m:g} m) differs from the preset ground elevation "
                        f"({float(matched_site['elevation_m']):g} m); raw angles are available, but terrain-fused KPIs are withheld."
                    )

        reference_kpis = compute_reference_kpis(
            ephemeris_check, antenna_height_m, los_margin_deg, timestep_hours, self.illum_svc)
        verified_dem, dem_report = self._verified_dem_for_site(eval_lat, eval_lon)
        observer_altitude_m = None
        if ephemeris_check and ephemeris_check.get("fixture"):
            _alt = (ephemeris_check["fixture"].get("coordinates") or {}).get("elevation_km")
            observer_altitude_m = None if _alt is None else float(_alt) * 1000.0
        altitude_match = observer_altitude_m is None or abs(observer_altitude_m - float(matched_site["elevation_m"])) <= 100.0
        if not altitude_match:
            reference_kpis = None
        real_engine_ready = bool(
            verified_dem is not None and ephemeris_check and altitude_match
            and dem_covers_site(verified_dem, eval_lat, eval_lon)
        )
        risk_assessment = evaluate_landing_site_risk(
            site_id=site_id,
            lat=eval_lat,
            lon=eval_lon,
            antenna_height_m=antenna_height_m,
            los_margin_deg=los_margin_deg,
            dem_dir=os.path.dirname(verified_dem.path) if verified_dem is not None else self.dem_svc.dem_dir,
        )

        # CASE 0: verified DEM covers the site and real Horizons angles exist -> terrain-aware engine
        if real_engine_ready:
            terrain = compute_terrain_aware(
                verified_dem, ephemeris_check, eval_lat, eval_lon,
                antenna_height_m, los_margin_deg, timestep_hours, self.illum_svc)
            terrain["terrain_info"]["dem_ingestion"] = dem_report
            terrain["kpis"].update({
                "max_amsi": matched_site["max_amsi"],
                "avg_asia_hours": matched_site["avg_asia_hours"],
                "composite_score": matched_site["baseline_score"],
                "composite_score_note": "Illustrative preset ranking index (weights: 40% illum, 35% dte, 15% darkness, 10% slope). NOT an official NASA score.",
                "landing_hazards_disclaimer": (
                    "REGIONAL SCREENING ONLY (80 m/px LOLA DEM): Evaluates topographic horizon masking and 80 m/px "
                    "bidirectional macro-slope from LDEM_80S_80MPP_ADJ.TIF. One 80m×80m pixel (6,400 m²) is ~28x larger "
                    "than a 15m lander pad (225 m²); does NOT certify final touchdown safety, which requires 0.5 m/px LROC NAC stereophotogrammetry."
                ),
                "tradeoffs": matched_site.get("tradeoffs", {}),
                "kpis_provenance": KPI_PROVENANCE_LABELS,
            })
            terrain["terrain_info"]["resolution_and_certification_boundary"] = risk_assessment["resolution_and_certification_boundary"]
            terrain["terrain_info"]["kpis_provenance"] = KPI_PROVENANCE_LABELS
            synthetic = verified_dem.is_synthetic
            n_eval = len(terrain["timeline"])
            demo_note = (
                " (Note: demo_mode=True was ignored because synthetic Demo fabrication is disabled in favor of the verified terrain engine.)"
                if demo_mode else ""
            )
            return {
                "status": "terrain_benchmark" if synthetic else "terrain_aware",
                "status_message": (
                    ("SYNTHETIC TERRAIN BENCHMARK: " if synthetic else f"TERRAIN-AWARE SCREENING ({verified_dem.meta['resolution_m_per_px']} m/px DEM — NOT FINAL PAD CERTIFICATION): ")
                    + f"real JPL Horizons angles for {n_eval} of {total_steps} steps were combined with a horizon mask "
                    f"ray-traced from DEM '{verified_dem.meta['product_id']}' ({verified_dem.meta['resolution_m_per_px']} m/px). "
                    "Steps without a Horizons sample are omitted, never extrapolated."
                    + demo_note
                ),
                "data_source": "synthetic_terrain_benchmark" if synthetic else "real_engine",
                "is_demo": synthetic,
                "inputs_used": inputs_echo,
                "coordinate_mismatch": coord_warning,
                "units": {
                    "illumination": "percentage (0-100%)",
                    "dte_connection": "geometric line-of-sight visibility percentage (0-100%). Unoccluded line-of-sight only.",
                    "antenna_height": "meters",
                    "los_margin": "degrees",
                    "elevation": "meters relative to 1737.4 km reference sphere",
                    "timestep": "hours",
                    "duration": "days",
                },
                "kpis": terrain["kpis"],
                "timeline": terrain["timeline"],
                "total_time_steps": total_steps,
                "ephemeris_check": ephemeris_check,
                "reference_kpis": reference_kpis,
                "terrain_info": terrain["terrain_info"],
                "landing_risk_assessment": risk_assessment,
                "validation_report": build_validation_report(
                    ephemeris_check=ephemeris_check, demo_mode=False, total_steps=total_steps,
                    timeline_length=n_eval, terrain_state="synthetic_benchmark" if synthetic else "ready"),
                "provenance": provenance,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }

        # CASE 1: DEM or ephemeris does not cover this site/date -> engine_pending (no synthetic fabrication)
        missing_reasons = []
        if verified_dem is None:
            missing_reasons.append("no verified LOLA DEM is loaded in dem_dir")
        elif not dem_covers_site(verified_dem, eval_lat, eval_lon):
            missing_reasons.append(f"coordinates ({eval_lat}, {eval_lon}) lie outside the loaded DEM extent")
        if not ephemeris_check:
            missing_reasons.append(
                "requested site/time is outside the recorded JPL Horizons fixture coverage (or no coordinate-matched fixture exists) and ENABLE_LIVE_HORIZONS is not enabled"
            )
        elif not altitude_match:
            missing_reasons.append("recorded Horizons observer altitude differs from the site ground-elevation baseline; raw ephemeris only")
        reason_str = "; ".join(missing_reasons) if missing_reasons else "terrain/ephemeris coverage incomplete"

        return {
            "status": "engine_pending",
            "status_message": (
                f"Terrain-aware time-series cannot be produced for this request because {reason_str}. "
                "Synthetic Demo fabrication is disabled for scientific integrity; no unverified KPIs or timeline points are fabricated."
            ),
            "data_source": "none",
            "is_demo": False,
            "inputs_used": inputs_echo,
            "coordinate_mismatch": coord_warning,
            "units": {
                "illumination": "percentage (0-100%)",
                "dte_connection": "percentage (0-100%)",
                "antenna_height": "meters",
                "los_margin": "degrees",
                "elevation": "meters relative to 1737.4 km reference sphere",
                "timestep": "hours",
                "duration": "days"
            },
            "kpis": None,
            "timeline": [],
            "total_time_steps": 0,
            "ephemeris_check": ephemeris_check,
            "reference_kpis": reference_kpis,
            "terrain_info": {
                "dem_ingestion": dem_report,
                "resolution_and_certification_boundary": risk_assessment["resolution_and_certification_boundary"],
            },
            "landing_risk_assessment": risk_assessment,
            "validation_report": build_validation_report(
                ephemeris_check=ephemeris_check,
                demo_mode=False,
                total_steps=total_steps,
                timeline_length=0,
            ),
            "provenance": provenance,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
