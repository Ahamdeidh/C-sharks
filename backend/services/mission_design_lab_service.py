"""Creative mission-design lab: explainable counterfactual scenario exploration."""
from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, Dict

FOCUS_AREAS = {
    "PeakNearShackleton": "Peak near Shackleton",
    "MalapertMassif": "Malapert Massif",
    "ConnectingRidge": "Connecting Ridge",
    "deGerlacheRim": "de Gerlache Rim",
    "Haworth": "Haworth",
}

MISSION_MODES = {
    "balanced": {"label": "Balanced Scout", "sun": 0.45, "communications": 0.35, "science": 0.20, "description": "A balanced first-pass trade across power, communications, and science access."},
    "solar_first": {"label": "Solar Continuity", "sun": 0.70, "communications": 0.20, "science": 0.10, "description": "Prioritizes long archive-derived illumination windows for power-constrained surface operations."},
    "communications_first": {"label": "Telecom Resilience", "sun": 0.20, "communications": 0.70, "science": 0.10, "description": "Prioritizes the source field labelled Sun+Earth as a communications proxy, not as verified DTE."},
    "science_first": {"label": "PSR Science", "sun": 0.20, "communications": 0.20, "science": 0.60, "description": "Prioritizes approximate PSR associations as a science-targeting signal."},
}


def _catalog() -> Dict[str, Any]:
    path = Path(__file__).parent.parent / "data" / "reference" / "lunar_catalog_v2.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _norm(value: float, values: list[float]) -> float:
    low, high = min(values), max(values)
    return 50.0 if high == low else round((value - low) / (high - low) * 100.0, 1)


def _sensitivity(base: list, metrics: Dict[str, list], draws: int = 4000, seed: int = 2026) -> Dict[str, Any]:
    """Rank stability when the three priority weights are drawn uniformly from the simplex."""
    rng = random.Random(seed)
    names = {row["area_id"]: row["name"] for row in base}
    normed = {row["area_id"]: {k: _norm(row[k], metrics[k]) for k in metrics} for row in base}
    first = {a: 0 for a in names}
    rank_sum = {a: 0 for a in names}
    best = {a: len(names) for a in names}
    worst = {a: 1 for a in names}
    for _ in range(draws):
        raw = [rng.expovariate(1.0) for _ in metrics]
        total = sum(raw)
        w = dict(zip(metrics, (r / total for r in raw)))
        order = sorted(names, key=lambda a: (-sum(normed[a][k] * w[k] for k in metrics), a))
        for rank, a in enumerate(order, 1):
            rank_sum[a] += rank
            best[a] = min(best[a], rank)
            worst[a] = max(worst[a], rank)
        first[order[0]] += 1
    rows = sorted((
        {"area_id": a, "name": names[a], "top_rank_share_pct": round(100.0 * first[a] / draws, 1),
         "mean_rank": round(rank_sum[a] / draws, 2), "best_rank": best[a], "worst_rank": worst[a]}
        for a in names), key=lambda r: (-r["top_rank_share_pct"], r["mean_rank"]))
    leader = rows[0]
    return {
        "method": "Monte Carlo over uniformly random priority weights on the 3-factor simplex",
        "draws": draws,
        "seed": seed,
        "regions": rows,
        "most_robust_first_choice": leader["name"],
        "robust_first_choice": leader["top_rank_share_pct"] >= 60.0,
        "interpretation": (
            f"{leader['name']} ranks first in {leader['top_rank_share_pct']}% of random weightings. "
            + ("The shortlist head is robust to the choice of weights." if leader["top_rank_share_pct"] >= 60.0
               else "No region dominates: the ranking depends strongly on the chosen priorities.")
            + " Robustness to weights says nothing about the validity of the underlying archive fields."
        ),
    }


def build_design_lab(catalog: Dict[str, Any] | None = None) -> Dict[str, Any]:
    catalog = catalog or _catalog()
    base = []
    for key, name in FOCUS_AREAS.items():
        area = catalog["areas"].get(key)
        if area:
            base.append({
                "area_id": key,
                "name": name,
                "sun": area["series"]["sun_only"]["mean_days_all_years"],
                "communications": area["series"]["sun_plus_earth"]["mean_days_all_years"],
                "science": area.get("psr_polygons_in_extent", 0),
            })
    metrics = {key: [row[key] for row in base] for key in ("sun", "communications", "science")}
    scenarios = []
    for mode_id, mode in MISSION_MODES.items():
        ranked = []
        for row in base:
            parts = {key: _norm(row[key], metrics[key]) for key in metrics}
            score = round(sum(parts[key] * mode[key] for key in metrics), 1)
            ranked.append({
                "area_id": row["area_id"],
                "name": row["name"],
                "score": score,
                "contribution": {"solar": round(parts["sun"] * mode["sun"], 1), "communications": round(parts["communications"] * mode["communications"], 1), "science": round(parts["science"] * mode["science"], 1)},
                "raw_evidence": {"sun_mean_days": row["sun"], "source_field_mean_days": row["communications"], "approx_psr_polygons": row["science"]},
            })
        ranked.sort(key=lambda item: (-item["score"], item["name"]))
        for rank, item in enumerate(ranked, 1): item["rank"] = rank
        scenarios.append({"mode_id": mode_id, **mode, "ranked_regions": ranked, "creative_question": f"If the team changed its mission priority to {mode['label']}, which region would move and why?"})
    return {
        "lab_type": "counterfactual_mission_design_lab",
        "title": "Mission Design Lab",
        "concept": "Explore how different mission priorities change the shortlist instead of treating one ranking as universally correct.",
        "scenarios": scenarios,
        "sensitivity": _sensitivity(base, metrics),
        "novelty": [
            "Counterfactual weighting makes mission priorities explicit and reversible.",
            "Every score decomposes into solar, communications, and science contributions.",
            "The same evidence can produce different operational concepts without hiding the trade-off.",
        ],
        "limitations": [
            "This is an explainable design exploration, not a scientifically validated optimizer.",
            "The communications signal uses an archive field named Sun+Earth with an unverified definition; it is not verified DTE.",
            "PSR associations are approximate and the project does not certify landing safety.",
        ],
    }
