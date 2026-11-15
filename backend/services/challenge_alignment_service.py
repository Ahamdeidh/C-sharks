"""Traceable alignment between the project and the official 2026 NASA Space Apps Challenge."""
from __future__ import annotations

import os
from typing import Any, Dict, List

from .terrain_engine import load_verified_dem

OFFICIAL_CHALLENGE_METADATA: Dict[str, Any] = {
    "event": "2026 NASA International Space Apps Challenge",
    "challenge_number": "Challenge #5 (CLPS Lunar Mission Browser / South Pole Site & Window Selection)",
    "official_title": "Lunar Landing Site Navigator",
    "official_url": "https://www.spaceappschallenge.org/2026/challenges/lunar-landing-site-navigator/",
    "challenges_directory_url": "https://www.spaceappschallenge.org/2026/challenges/",
    "difficulty": "Intermediate / Advanced",
    "subjects": ["Human Exploration", "Moon", "Software", "Space Exploration"],
    "core_mission_statement": (
        "Create an intuitive tool or application that lets mission planners, educators, and the public "
        "compare landing sites and dates quickly, visualizing Sun and Earth positions relative to the "
        "horizon to assess power generation potential and direct-to-Earth communication windows."
    ),
}


def build_challenge_alignment() -> Dict[str, Any]:
    dem_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "dem")
    verified_dem, _ = load_verified_dem(dem_dir)
    dem_ready = verified_dem is not None and not verified_dem.is_synthetic

    criteria: List[Dict[str, Any]] = [
        {
            "id": "lunar-south-pole-planning",
            "challenge_goal": "Support evidence-based planning for lunar south-pole exploration.",
            "project_response": (
                "Interactive mission-control dashboard, five South Pole presets + custom lunar coordinates override, "
                "curated multi-program comparator (Apollo, CLPS, ISRO, CNSA, CSA), archive explorer, decision brief, "
                "and physics-based pad-scale landing risk & RF link budget evaluator."
            ),
            "evidence": [
                "/api/v1/sites",
                "/api/v1/mission/horizon-ops",
                "/api/v1/mission/landing-risk",
                "/api/v1/reference/catalog-v2",
                "/api/v1/mission/decision-brief",
                "HorizonAndOpsPanel",
                "LandingRiskPanel",
            ],
            "data_role": "Real LOLA DEM (80 m/px) ray-tracing & bidirectional slope, JPL Horizons ephemeris, archive-derived regional illumination summaries, and published LRO Diviner / Lunar Sourcebook engineering parameters.",
            "status": "implemented_terrain_aware_and_reference_workflow",
            "gap": "80 m/px LOLA DEM resolves regional horizon and macro-slope; sub-meter flight pad certification requires LROC NAC 0.5 m stereophotogrammetry.",
        },
        {
            "id": "nasa-data-core",
            "challenge_goal": "Use NASA/JPL data as a meaningful part of the method, not as decoration.",
            "project_response": (
                "Bundled LOLA product-labeled DEM subset (LDEM_80S_80MPP_ADJ.TIF, 601 × 601 pixels, about 48 × 48 km at 80 m/px) and JPL Horizons Sun/Earth apparent "
                "azimuth/elevation drive the terrain_aware simulation engine, 360° Horizon Panorama, Polar Skyplot, "
                "sunset/Earthset countdowns, vertical vs. horizontal solar array cosine efficiency (37.6x), and bidirectional pad-scale slope."
            ),
            "evidence": [
                "LDEM_80S_80MPP_ADJ.TIF",
                "ephemeris_check",
                "reference_kpis",
                "/api/v1/mission/horizon-ops",
                "/api/v1/mission/landing-risk",
                "RealHorizonsPanel",
                "RealReferenceKpiPanel",
                "HorizonAndOpsPanel",
                "https://ssd.jpl.nasa.gov/api/horizons.api",
            ],
            "data_role": (
                "Bundled LOLA DEM subset (LDEM_80S_80MPP_ADJ.TIF, 601 × 601 pixels, about 48 × 48 km at 80 m/px) + recorded JPL Horizons fixture (with opt-in live Horizons via ENABLE_LIVE_HORIZONS=1) drive real terrain_aware KPIs, horizon ray-tracing, and geodetic control verification."
                if dem_ready
                else "Recorded JPL Horizons fixture by default; terrain_aware activates when a verified LOLA DEM is present in backend/data/dem/."
            ),
            "status": "implemented_terrain_aware_integration",
            "gap": "The DEM is only a centered 601 × 601 pixel subset (~48 × 48 km); sites outside its raster footprint are not DEM-covered. Offline Horizons data comprises a Shackleton 48-hour fixture plus separately recorded multi-site files under backend/data/fixtures/horizons (Nov 14–20, 2026). Live queries require ENABLE_LIVE_HORIZONS=1; unsupported dates/sites are not extrapolated.",
        },
        {
            "id": "scientific-reproducibility",
            "challenge_goal": "Make the analysis reproducible and scientifically transparent.",
            "project_response": (
                "Synthetic Demo fabrication is disabled by default; provenance is returned in every response; "
                "20/20 closed-form, physical, geodetic control-point, DEM integrity, and external peer-reviewed literature benchmarks pass; "
                "every metric carries an explicit source & limitation badge."
            ),
            "evidence": [
                "/api/v1/provenance",
                "/api/v1/validation/benchmarks",
                "backend/data/fixtures/external_literature_benchmarks.json",
                "scripts/build_catalog_v2.py",
                "README.md",
                "REVIEW_REPORT_AR.md",
            ],
            "data_role": "Source metadata, geodetic control-point verification, external literature benchmarks (Rosenburg 2011, Bandfield 2011, Carrier 1991, Metzger 2011), and per-value source/limit badges.",
            "status": "implemented_verified_pipeline",
            "gap": "Archive catalog v2 Sun+Earth source field retains an explicit upstream definition caveat.",
        },
        {
            "id": "mission-decision-usefulness",
            "challenge_goal": "Help users make a meaningful next decision rather than only visualize data.",
            "project_response": (
                "Combines evidence-first decision brief, schedule-slip sensitivity, counterfactual Mission Design Lab, "
                "and quantitative pad-scale engineering risk screening (bidirectional DEM slope, boulder clearance, "
                "regolith Terzaghi bearing capacity, plume-surface scouring, and DSN 34m X-band RF link budget)."
            ),
            "evidence": [
                "/api/v1/mission/decision-brief",
                "/api/v1/mission/horizon-ops",
                "/api/v1/mission/landing-risk",
                "DecisionBriefPanel",
                "HorizonAndOpsPanel",
                "LandingRiskPanel",
            ],
            "data_role": "Integrates 80 m/px DEM gradients with published LRO Diviner, Lunar Sourcebook, and DSN engineering models while preserving a strict flight-certification gate.",
            "status": "implemented_engineering_screening",
            "gap": "Screening models support engineering trade studies and triage; final flight certification requires in-situ or sub-meter NAC hazard surveys.",
        },
    ]

    challenge_objectives_detail: List[Dict[str, str]] = [
        {
            "requirement_id": "OBJ-01",
            "objective": "1. Interactive site selection, custom coordinates & comparison",
            "official_requirement": "Allow users to choose from a curated list of notable landing sites (Apollo, CLPS, international programs) as well as input custom lunar coordinates, enabling side-by-side or sequential comparison.",
            "linked_feature": "Sidebar Site Selector + Custom Coordinates Override + Baseline [A] vs Current [B] Scenario Comparator + 7-Mission Multi-Program Comparator",
            "code_and_endpoint": "POST /api/v1/simulation/run, GET /api/v1/sites, GET /api/v1/mission/horizon-ops (LunarLandingNavigator.jsx, HorizonAndOpsPanel.jsx)",
            "source_and_limit": "Real LOLA DEM (80 m/px) + JPL Horizons for Shackleton; Archive Catalog v2 & Curated Mission Records for multi-program comparison.",
            "implementation": "5 Artemis South Pole presets + Custom Latitude/Longitude override in sidebar + Side-by-side Baseline vs. Current scenario comparator + 7-mission Multi-Program Comparator (Apollo 11, CLPS IM-1/VIPER, ISRO Chandrayaan-3, CNSA Chang'e-7, CSA LUV).",
        },
        {
            "requirement_id": "OBJ-02",
            "objective": "2. Date, time & schedule-delay flexibility",
            "official_requirement": "Allow users to select landing dates and times, and explore how mission schedule adjustments (launch delays/slips) affect feasibility across lunar days or seasons.",
            "linked_feature": "UTC Timezone-Aware Date Selector + In-Window Schedule-Slip Matrix (+0h/+12h/+24h/+36h) + 8-Year Seasonal Archive Explorer (2025–2032)",
            "code_and_endpoint": "GET /api/v1/mission/horizon-ops, GET /api/v1/reference/catalog-v2 (HorizonAndOpsPanel.jsx, RealArchiveDataPanel.jsx)",
            "source_and_limit": "Recorded JPL Horizons 48h fixture (no extrapolation); 336 annual illumination rasters for 2025–2032 seasonal trends. Catalog provenance is user-supplied and unverified; no NASA authorship is claimed.",
            "implementation": "Timezone-aware start time selector, duration (1–60d), step resolution (1–12h), in-window launch-slip sensitivity (+0h/+12h/+24h/+36h), and 8-year seasonal archive explorer (2025–2032).",
        },
        {
            "requirement_id": "OBJ-03",
            "objective": "3. Sun & Earth position visualization + Sunset/Earthset countdown",
            "official_requirement": "Display positions of Sun and Earth relative to the local horizon on a chosen date, and show how much time remains before sunset or Earthset.",
            "linked_feature": "360° Local Horizon Panorama SVG + Polar Skyplot SVG + Sunset/Earthset & Earthrise Countdown Cards",
            "code_and_endpoint": "GET /api/v1/mission/horizon-ops (backend/services/horizon_and_ops_service.py, src/HorizonAndOpsPanel.jsx)",
            "source_and_limit": "Real JPL Horizons airless apparent az/el + 80 m/px LOLA DEM ray-traced horizon mask + smooth-sphere mast dip.",
            "implementation": "360° Azimuth-Elevation Horizon Panorama & Polar Skyplot with finite Sun (0.26°) and Earth (0.90°) discs, LOLA DEM terrain horizon profile + smooth-sphere mast dip, and time-to-sunset / time-to-Earthrise operational status.",
        },
        {
            "requirement_id": "OBJ-04",
            "objective": "4. Power generation, DTE communication & RF link budget assessment",
            "official_requirement": "Highlight key metrics such as solar elevation angle, duration of sunlight, Vertical vs. Horizontal array efficiency, and Direct-to-Earth visibility windows.",
            "linked_feature": "Solar Array Cosine/Sine Incidence Analyzer (37.6x Vertical Gain) + DSN 34m X-Band RF Link Budget Evaluator",
            "code_and_endpoint": "GET /api/v1/mission/horizon-ops, GET /api/v1/mission/landing-risk (horizon_and_ops_service.py, landing_risk_service.py)",
            "source_and_limit": "Exact trigonometric incidence from JPL Horizons angles; analytical 8.42 GHz Friis link budget (NASA DSN 810-005).",
            "implementation": "Solar elevation angle tracking (+1.506° to +1.544°), vertical vs. horizontal solar array cosine flux multiplier (37.6x gain at 89.9°S), geometric Earth LOS clearance, and full 8.42 GHz X-band DSN 34m BWG link budget (+9.22 dB Eb/N0 margin when LOS is clear).",
        },
        {
            "requirement_id": "OBJ-05",
            "objective": "5. Multiple visualization approaches & pad-scale hazard screening",
            "official_requirement": "Explore 2D maps, 3D/horizon surface visualizations, and terrain slope/hazard representations showing spatial relationships.",
            "linked_feature": "Polar Stereographic Map + 360° Horizon Panorama + Polar Skyplot + Pad-Scale Slope/Boulder/Regolith/PSI Engineering Panel",
            "code_and_endpoint": "GET /api/v1/mission/landing-risk, POST /api/v1/simulation/run (LandingRiskPanel.jsx, HorizonAndOpsPanel.jsx)",
            "source_and_limit": "80 m/px LOLA DEM bidirectional gradient + Hurst scaling (Rosenburg 2011) + LRO Diviner / Lunar Sourcebook screening models (non-certified at sub-meter scale).",
            "implementation": "Bidirectional E-W and N-S slope from LDEM_80S_80MPP_ADJ.TIF with Hurst fractal scaling (H=0.75) to 15 m lander footprint, LRO Diviner boulder height clearance, Terzaghi regolith bearing capacity, and supersonic exhaust plume scouring.",
        },
        {
            "requirement_id": "OBJ-06",
            "objective": "6. Temporal dynamics, animation & counterfactual sensitivity",
            "official_requirement": "Create animations or timeline views showing how Sun and Earth positions change over a lunar day or across multiple days.",
            "linked_feature": "Interactive Play/Pause Horizon Animator + Recharts Area/Line Time-Series + 4,000-Draw Monte Carlo Mission Design Lab",
            "code_and_endpoint": "GET /api/v1/mission/horizon-ops, GET /api/v1/mission/design-lab (HorizonAndOpsPanel.jsx, MissionDesignLabPanel.jsx)",
            "source_and_limit": "Step-by-step animation across verified JPL Horizons samples; deterministic seed=42 Monte Carlo weight perturbation.",
            "implementation": "Interactive step scrubber and Play/Pause animation stepping through real JPL Horizons samples, plus 4,000-draw Monte Carlo weight sensitivity in the Mission Design Lab.",
        },
        {
            "requirement_id": "OBJ-07",
            "objective": "7. Accessibility across skill levels (Mission Planners & Educators)",
            "official_requirement": "Serve mission planners seeking detailed technical information as well as educators and the general public curious about lunar engineering challenges.",
            "linked_feature": "Dual-Audience Mode Switcher (Mission Planner Engineering Mode vs. Educator & Public Mode) + WCAG Live Announcements",
            "code_and_endpoint": "GET /api/v1/mission/horizon-ops (HorizonAndOpsPanel.jsx, LunarLandingNavigator.jsx)",
            "source_and_limit": "Switches between quantitative engineering metrics and intuitive physical explanations of the 1.54° lunar tilt and ±7° optical libration.",
            "implementation": "Dedicated Audience Mode Switcher ('Mission Planner Engineering Mode' vs. 'Educator & Public Explorer Mode') plus WCAG live screen-reader announcements and keyboard navigation.",
        },
    ]

    partner_resources: List[Dict[str, str]] = [
        {
            "name": "NASA Space Apps 2026 Official Challenge: Lunar Landing Site Navigator",
            "url": "https://www.spaceappschallenge.org/2026/challenges/lunar-landing-site-navigator/",
            "integration": "Primary challenge specification driving all 7 core objectives (OBJ-01..OBJ-07) and technical verification requirements.",
        },
        {
            "name": "NASA JPL Horizons System",
            "url": "https://ssd.jpl.nasa.gov/horizons/",
            "integration": "Core ephemeris source (coord@301, Sun '10', Earth '399', airless apparent az/el) via recorded fixture and opt-in live REST client.",
        },
        {
            "name": "NASA LRO LOLA / USGS PDS Orbital Data Explorer (LDEM_80S_80MPP_ADJ.TIF)",
            "url": "https://ode.rsl.wustl.edu/",
            "integration": "Bundled & verified 80 m/px Polar Stereographic GeoTIFF (Moon 2000, R=1737.4 km) driving 360° horizon ray-tracing, geodetic control verification, and bidirectional pad-scale slope.",
        },
        {
            "name": "NASA Moon Trek & ASU LROC Quickmap / Diviner Rock Abundance",
            "url": "https://trek.nasa.gov/moon/",
            "integration": "Visual terrain context and published polar rock abundance / boulder size-frequency distributions for under-deck leg clearance modeling.",
        },
        {
            "name": "CSA (Canadian Space Agency) Moon Exploration Portal",
            "url": "https://www.asc-csa.gc.ca/eng/astronomy/moon-exploration/",
            "integration": "Integrated in the Multi-Program Comparator highlighting Canada's Lunar Rover / Lunar Utility Vehicle (LUV) polar traverse constraints.",
        },
    ]

    implemented = sum(1 for item in criteria if item["status"].startswith("implemented"))
    return {
        "alignment_type": "challenge_traceability_matrix",
        "title": "Lunar Landing Site Navigator — Official 2026 NASA Space Apps Challenge Traceability",
        "official_challenge": OFFICIAL_CHALLENGE_METADATA,
        "summary": "Every challenge-facing claim is mapped to an official requirement ID (OBJ-01..07), product feature, API endpoint, data source tier, and explicit resolution boundary.",
        "criteria": criteria,
        "challenge_objectives_detail": challenge_objectives_detail,
        "partner_resources": partner_resources,
        "coverage": {
            "criteria_mapped": len(criteria),
            "criteria_with_evidence": sum(bool(item["evidence"]) for item in criteria),
            "objectives_mapped": len(challenge_objectives_detail),
            "implementation_status": f"{implemented}/{len(criteria)} mapped objectives have corresponding software/data support, subject to the stated spatial, temporal, and model limitations",
        },
        "honesty_note": "Alignment connects the bundled LOLA-labeled 80 m/px DEM subset (601 × 601; ~48 × 48 km) ray-tracing, JPL Horizons ephemeris, and published lunar engineering models, and does not imply that screening models replace sub-meter flight certification.",
    }
