"""Tests for the Pad-Scale Landing Site Risk, Boulders, Regolith, Plume-Surface Interaction & RF Link Budget Service."""
from fastapi.testclient import TestClient

from main import app
from services.landing_risk_service import evaluate_landing_site_risk

client = TestClient(app)


def test_landing_risk_evaluates_all_five_engineering_domains_by_default():
    res = evaluate_landing_site_risk(site_id="shackleton", lat=-89.9, lon=0.0)
    assert res["status"] == "evaluated"
    assert res["blocked_components"] == 0
    assert res["pad_scale_topography"]["source"] == "real_lola_dem_bidirectional_gradient"
    assert "slope_east_west_deg" in res["pad_scale_topography"]
    assert "slope_north_south_deg" in res["pad_scale_topography"]
    assert "pad_scale_effective_slope_deg" in res["pad_scale_topography"]
    comps = res["components"]
    assert set(comps) == {"boulder_hazard", "regolith_bearing", "plume_surface_interaction", "rf_link_budget"}
    assert comps["boulder_hazard"]["status"] == "screening_only"
    assert comps["regolith_bearing"]["status"] == "screening_only"
    assert res["pad_scale_topography"]["status"] == "screening_only"
    assert comps["rf_link_budget"]["status"] in {"pass", "caution"}


def test_boulder_clearance_responds_to_lander_belly_height():
    low = evaluate_landing_site_risk(site_id="shackleton", lander_belly_clearance_m=0.30)
    high = evaluate_landing_site_risk(site_id="shackleton", lander_belly_clearance_m=0.85)
    assert high["components"]["boulder_hazard"]["under_deck_clearance_margin_m"] > low["components"]["boulder_hazard"]["under_deck_clearance_margin_m"]
    assert high["components"]["boulder_hazard"]["status"] == "screening_only"
    assert low["components"]["boulder_hazard"]["status"] == "screening_only"
    assert high["components"]["boulder_hazard"]["clean_25m_pad_probability_pct"] is None


def test_regolith_terzaghi_bearing_capacity_and_sinkage():
    light = evaluate_landing_site_risk(site_id="shackleton", lander_mass_kg=800.0)
    heavy = evaluate_landing_site_risk(site_id="shackleton", lander_mass_kg=4500.0)
    assert light["components"]["regolith_bearing"]["bearing_safety_factor"] > heavy["components"]["regolith_bearing"]["bearing_safety_factor"]
    assert heavy["components"]["regolith_bearing"]["estimated_footpad_sinkage_cm"] > light["components"]["regolith_bearing"]["estimated_footpad_sinkage_cm"]


def test_plume_surface_interaction_scales_with_descent_thrust():
    low_t = evaluate_landing_site_risk(site_id="shackleton", descent_thrust_n=8000.0)
    high_t = evaluate_landing_site_risk(site_id="shackleton", descent_thrust_n=35000.0)
    assert high_t["components"]["plume_surface_interaction"]["predicted_scour_depth_cm"] > low_t["components"]["plume_surface_interaction"]["predicted_scour_depth_cm"]
    assert high_t["components"]["plume_surface_interaction"]["transient_dust_optical_depth"] > low_t["components"]["plume_surface_interaction"]["transient_dust_optical_depth"]


def test_rf_link_budget_computes_x_band_fspl_and_eb_n0_margin():
    rf = evaluate_landing_site_risk(site_id="malapert", lat=-85.9, lon=-2.9, rf_tx_power_w=20.0, rf_data_rate_mbps=1.0)["components"]["rf_link_budget"]
    assert rf["frequency_ghz"] == 8.42
    assert 222.0 <= rf["free_space_path_loss_db"] <= 223.5
    assert rf["rf_link_margin_when_los_clear_db"] > 3.0
    assert rf["geometric_dte_los_clear_in_nov2026_window"] is True
    assert rf["status"] == "pass"


def test_strict_field_certification_gate_blocks_without_in_situ_surveys():
    blocked = evaluate_landing_site_risk(site_id="shackleton", strict_field_certification_only=True)
    assert blocked["status"] == "blocked"
    assert all(blocked["components"][k]["status"] == "blocked" for k in blocked["components"])


def test_landing_risk_endpoint_and_simulation_integration():
    res = client.get("/api/v1/mission/landing-risk?site_id=shackleton&lat=-89.9&lon=0.0")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "evaluated"
    assert body["blocked_components"] == 0


def test_independent_literature_validation_and_provenance_badges():
    res = evaluate_landing_site_risk(site_id="shackleton", lat=-89.9, lon=0.0)
    ext = res["independent_literature_validation"]
    assert len(ext) == 5
    assert all("not_independent_validation" in row["agreement_status"] or row["agreement_status"] == "not_evaluated_no_pad_scale_measurement" for row in ext)
    boundary = res["resolution_and_certification_boundary"]
    assert boundary["dem_pixel_size_m"] == 80.0
    assert boundary["lander_pad_span_m"] == 15.0
    assert "source_badge" in res["pad_scale_topography"]
    assert "limitation_badge" in res["pad_scale_topography"]
    for comp in res["components"].values():
        assert "source_badge" in comp and "limitation_badge" in comp


def test_rock_fraction_is_disclosed_as_curated_assumption():
    result = evaluate_landing_site_risk(site_id="shackleton", lat=-89.9, lon=0.0)
    boulder = result["components"]["boulder_hazard"]
    assert "[Curated Assumption]" in boulder["rock_abundance_label"]
    assert "Not extracted" in boulder["rock_abundance_label"]
    assert "Bandfield" in boulder["rock_abundance_citation"]

def test_landing_risk_marks_outside_dem_and_profile_fallback():
    result = evaluate_landing_site_risk(site_id="shackleton", lat=-80.0, lon=0.0)
    assert result["dem_coverage"]["covered"] is False
    assert "not site-specific DEM measurements" in result["dem_coverage"]["warning"]


def test_site01_high_resolution_tile_is_not_activated_when_vertical_check_conflicts():
    from services.simulation_engine import SimulationEngine
    engine = SimulationEngine()
    dem, report = engine._verified_dem_for_site(-89.4, 222.0)
    assert dem is not None and dem.meta["resolution_m_per_px"] == 80.0
    assert report["selection"] == "regional_fallback"
    assert report["challenge_tile_rejection"].startswith("elevation disagreement")
    assert report["challenge_tile_cross_check"]["absolute_difference_m"] > 2000
