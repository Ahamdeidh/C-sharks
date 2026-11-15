"""Evidence-first mission decision brief built from the supplied archive catalog
and connected to the verified LOLA DEM (`LDEM_80S_80MPP_ADJ.TIF`) status.

This is a regional triage and engineering screening aid, not a flight landing
certificate. It deliberately keeps archive reference data separate from the
time-resolved simulation engine.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List

from .terrain_engine import load_verified_dem

FOCUS_AREAS = {
    "PeakNearShackleton": "Peak near Shackleton",
    "MalapertMassif": "Malapert Massif",
    "ConnectingRidge": "Connecting Ridge",
    "deGerlacheRim": "de Gerlache Rim",
    "Haworth": "Haworth",
}


def _load_catalog(path: Path | None = None) -> Dict[str, Any]:
    catalog_path = path or Path(__file__).parent.parent / "data" / "reference" / "lunar_catalog_v2.json"
    return json.loads(catalog_path.read_text(encoding="utf-8"))


def _bounded(value: float, low: float, high: float) -> float:
    if high <= low:
        return 50.0
    return round(max(0.0, min(100.0, (value - low) / (high - low) * 100.0)), 1)


def build_decision_brief(catalog: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Create a conservative, reproducible shortlist from catalog-v2 and DEM readiness."""
    catalog = catalog or _load_catalog()
    dem_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "dem")
    verified_dem, _ = load_verified_dem(dem_dir)
    dem_status_note = (
        f"Verified LOLA DEM ({verified_dem.meta['product_id']}, {verified_dem.meta['resolution_m_per_px']} m/px) is active for regional horizon ray-tracing; sub-meter LROC NAC stereophotogrammetry is still required for final pad certification."
        if verified_dem is not None
        else "No verified LOLA elevation DEM is currently loaded in backend/data/dem/."
    )

    rows: List[Dict[str, Any]] = []
    for key, label in FOCUS_AREAS.items():
        area = catalog["areas"].get(key)
        if not area:
            continue
        sun = area["series"]["sun_only"]["mean_days_all_years"]
        sun_earth = area["series"]["sun_plus_earth"]["mean_days_all_years"]
        psr = area.get("psr_polygons_in_extent", 0)
        rows.append({
            "area_id": key,
            "name": label,
            "center_lat_lon": area["center_lat_lon"],
            "sun_only_mean_days": sun,
            "sun_plus_earth_mean_days": sun_earth,
            "approx_psr_polygons": psr,
            "data_classification": "archive_catalog_v2_regional_triage",
        })

    sun_values = [r["sun_only_mean_days"] for r in rows]
    earth_values = [r["sun_plus_earth_mean_days"] for r in rows]
    for row in rows:
        sun_score = _bounded(row["sun_only_mean_days"], min(sun_values), max(sun_values))
        earth_score = _bounded(row["sun_plus_earth_mean_days"], min(earth_values), max(earth_values))
        row["triage_index"] = round(0.6 * sun_score + 0.4 * earth_score, 1)
        row["evidence"] = [
            f"{row['sun_only_mean_days']:.2f} d multi-year Sun-only archive mean",
            f"{row['sun_plus_earth_mean_days']:.2f} d archive mean for the source field named Sun+Earth",
            f"{row['approx_psr_polygons']} approximate PSR centroid assignments",
        ]
        row["blockers"] = [
            dem_status_note,
            "The archive source field named Sun+Earth has an unverified upstream definition and is not DTE availability.",
            "PSR counts are approximate rectangle/centroid associations.",
        ]
        row["recommended_next_action"] = (
            "Run time-resolved LOLA DEM + JPL Horizons simulation and inspect pad-scale slope, boulder clearance, regolith bearing, and RF link margin before mission selection."
        )

    rows.sort(key=lambda r: (-r["triage_index"], -r["sun_only_mean_days"], r["name"]))
    for rank, row in enumerate(rows, start=1):
        row["rank"] = rank
        row["decision"] = "shortlist for next analysis" if rank <= 2 else "retain as comparison candidate"

    return {
        "brief_type": "evidence_first_mission_triage",
        "title": "South-pole mission decision brief",
        "status": "reference_triage_only",
        "purpose": "Prioritize candidate regions using archive-derived regional summaries and link them to LOLA DEM ray-tracing and pad-scale engineering risk screening.",
        "mission_questions": [
            "Which regions combine high multi-year illumination with manageable pad-scale slope and boulder risk?",
            "Where do archive illumination summaries justify sub-meter NAC hazard mapping?",
            "What engineering margins (mast height, boulder clearance, RF link budget) govern site selection?",
        ],
        "thresholds": {
            "preferred_sun_only_mean_days": 7.0,
            "preferred_source_field_mean_days": 7.0,
            "note": "Thresholds are triage gates selected for prioritization, not flight certification requirements.",
        },
        "ranked_regions": rows,
        "recommended_work_packages": [
            {"priority": 1, "action": "Execute LOLA DEM (80 m/px) horizon ray-tracing and bidirectional pad-scale slope check across candidate coordinates.", "unlocks": "Terrain-aware illumination, Earth LOS, and macro-slope screening."},
            {"priority": 2, "action": "Evaluate boulder clearance, Terzaghi regolith bearing capacity, plume scouring, and DSN 34m X-band RF link budget via /api/v1/mission/landing-risk.", "unlocks": "Integrated multi-disciplinary engineering trade study."},
            {"priority": 3, "action": "Acquire sub-meter (0.5 m/px) LROC NAC stereophotogrammetry and live multi-epoch JPL Horizons queries.", "unlocks": "Pad-level hazard certification across extended launch windows."},
            {"priority": 4, "action": "Verify upstream publisher and processing lineage for the supplied GIS illumination archives.", "unlocks": "Traceable reconciliation between annual archive rasters and time-resolved Horizons runs."},
        ],
        "limitations": [
            catalog["provenance_warning"],
            catalog["units_note"],
            "This brief ranks reference regions only; it is not a landing certificate, does not replace the simulation engine, and does not certify safety, power, or communications availability.",
        ],
        "provenance": {
            "catalog_version": catalog["version"],
            "raster_products": catalog["counts"]["rasters"],
            "areas": catalog["counts"]["areas"],
            "psr_polygons": catalog["counts"]["psr_polygons"],
            "dem_status": dem_status_note,
            "ranking_formula": "60% normalized Sun-only mean days + 40% normalized source-field mean days; reference triage index only.",
        },
    }
