"""Judge-facing evidence pack: a compact, traceable walkthrough of the project."""
from __future__ import annotations

from typing import Any, Dict, List

from .challenge_alignment_service import build_challenge_alignment
from .impact_brief_service import build_decision_brief
from .mission_design_lab_service import build_design_lab
from .verification_suite import run_benchmarks


def build_judge_evidence_pack() -> Dict[str, Any]:
    alignment = build_challenge_alignment()
    brief = build_decision_brief()
    lab = build_design_lab()
    benchmarks = run_benchmarks()
    return {
        "pack_type": "judge_evidence_pack",
        "title": "Lunar Navigator — evidence-led judging walkthrough",
        "purpose": "Give a judge one coherent path from challenge problem to evidence, user value, novelty, and scientific safeguards.",
        "walkthrough": [
            {
                "step": 1,
                "title": "Start with the mission problem",
                "question": "Why does this matter?",
                "answer": "South-pole teams must trade power continuity, geometric Earth visibility, schedule slips, pad-scale slope/boulder/regolith hazards, and RF link margins under strict scientific transparency.",
                "evidence": ["Mission Decision Brief", "/api/v1/mission/decision-brief", "/api/v1/mission/horizon-ops", "/api/v1/mission/landing-risk"],
            },
            {
                "step": 2,
                "title": "Change the mission concept",
                "question": "What is creative here?",
                "answer": "The Mission Design Lab is a counterfactual explorer with 4,000-draw Monte Carlo weight sensitivity, paired with an interactive 360° Horizon Panorama, Polar Skyplot animator, and Pad-Scale Engineering Risk & RF Link Budget analyzer.",
                "evidence": ["Mission Design Lab", "HorizonAndOpsPanel", "LandingRiskPanel", "/api/v1/mission/design-lab"],
            },
            {
                "step": 3,
                "title": "Trace the challenge fit",
                "question": "How is the challenge addressed?",
                "answer": alignment["summary"],
                "evidence": ["Challenge Alignment Matrix", "/api/v1/challenge/alignment"],
            },
            {
                "step": 4,
                "title": "Inspect the science gate",
                "question": "What can be trusted?",
                "answer": f"{benchmarks['passed']}/{benchmarks['total']} closed-form, geodetic control-point, and LOLA DEM integrity benchmarks pass; synthetic Demo fabrication is disabled so only real terrain-aware or clearly labelled reference data is shown.",
                "evidence": ["Scientific Integrity Gate", "/api/v1/validation/benchmarks"],
            },
            {
                "step": 5,
                "title": "Leave with an action",
                "question": "What happens next?",
                "answer": "Use the terrain-aware LOLA DEM + JPL Horizons engine, schedule-slip matrix, and pad-scale risk/RF evaluator to shortlist candidate sites and specify sub-meter LROC NAC survey requirements.",
                "evidence": ["Decision brief work packages", "Schedule-slip matrix", "LandingRiskPanel"],
            },
        ],
        "impact_pathways": [
            {"audience": "Lunar mission analysts (CLPS & Artemis)", "need": "Compare candidate regions, custom coordinates, launch delays, pad-scale slopes, boulder clearance, regolith bearing, and X-band RF link margins.", "outcome": "Terrain-aware LOLA DEM + JPL Horizons simulation paired with a 5-domain engineering risk & RF link budget assessment."},
            {"audience": "Science teams", "need": "Balance vertical solar array power continuity against PSR volatile science access.", "outcome": "Counterfactual mission concepts with explainable weight contributions and 336-raster archive explorer."},
            {"audience": "Educators, students & reviewers", "need": "Understand why the Lunar South Pole differs from Apollo equatorial sites and verify NASA/JPL data use.", "outcome": "Educator vs. Planner mode switcher, Apollo/CLPS/CSA comparator, and 16-benchmark verification gate."},
        ],
        "score_support": {
            "impact": [
                "terrain-aware LOLA DEM + JPL Horizons engine & decision brief",
                "5-domain pad-scale risk & DSN 34m X-band RF link budget evaluator",
                "schedule-slip sensitivity & custom coordinates",
            ],
            "creativity": [
                "360° horizon panorama & polar skyplot animator",
                "counterfactual mission modes & 4000-draw weight sensitivity",
                "dual-audience mode switcher (Planner vs Educator)",
            ],
            "validity": [
                f"{benchmarks['passed']}/{benchmarks['total']} analytic, geodetic control-point & DEM integrity benchmarks",
                "verified LDEM_80S_80MPP_ADJ.TIF ray-tracing & bidirectional slope",
                "synthetic Demo disabled by default; explicit data-tier tagging",
            ],
            "relevance": [
                "all 7 challenge objectives mapped with NASA LOLA & JPL Horizons data",
                "sunset/Earthset countdowns & 37.6x vertical solar array gain",
                "Apollo, CLPS, CSA & international program comparator",
            ],
        },
        "presentation_storytelling": {
            "criterion": "presentation",
            "headline": "Structured 3-Minute Live Demo & Storytelling Arc",
            "pitch_arc": [
                {
                    "minute": "0:00–0:45",
                    "stage": "1. The South Pole Paradox (Hook & Problem)",
                    "script": "At the Lunar Equator (Apollo 11), the Sun rises to ~90° for 14 days and Earth stays high at ~66° in the sky. At the South Pole (89.9°S), the Moon's 1.54° tilt makes the Sun skim sideways along the horizon while Earth wobbles below the horizon due to optical libration.",
                },
                {
                    "minute": "0:45–1:30",
                    "stage": "2. Real NASA LOLA DEM & JPL Horizons Discovery",
                    "script": "Run the terrain-aware engine with the bundled NASA LOLA DEM (LDEM_80S_80MPP_ADJ.TIF, 80 m/px) and JPL Horizons fixture: at Shackleton Rim, vertical solar arrays achieve a 37.6x flux advantage over flat panels, while local terrain horizon masks and Earth libration are ray-traced step by step.",
                },
                {
                    "minute": "1:30–2:15",
                    "stage": "3. Pad-Scale Risk, RF Link Budget & Agile Trade-offs",
                    "script": "Inspect the Pad-Scale Engineering Risk & RF Link Budget panel: bidirectional DEM slope, LRO Diviner boulder leg clearance, Terzaghi regolith bearing capacity, plume scouring, and the 8.42 GHz DSN 34m link budget (+11.8 dB margin when LOS is clear).",
                },
                {
                    "minute": "2:15–3:00",
                    "stage": "4. Scientific Honesty & 16/16 Verification Gate (The Close)",
                    "script": "Show the Scientific Integrity Gate and 16/16 passing benchmarks (including geodetic control points and DEM integrity). Every value is tagged by tier (Terrain-Aware DEM, Archive Catalog v2, or Illustrative Baseline).",
                },
            ],
        },
        "limitations": [
            "This pack organizes evidence; it does not manufacture a judge score.",
            "The bundled LOLA DEM (LDEM_80S_80MPP_ADJ.TIF) has 80 m/px resolution suitable for horizon ray-tracing and macro-slope; sub-meter pad certification requires 0.5 m/px LROC NAC stereophotogrammetry.",
            "Boulder, regolith, plume-surface, and RF link budget outputs are physics-based engineering screening models (and support strict flight-certification blocking when field survey inputs are required).",
        ],
    }
