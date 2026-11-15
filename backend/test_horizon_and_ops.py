"""Tests for the Horizon Panorama, Operational Countdowns, Schedule-Slip & Multi-Program Comparator."""
from fastapi.testclient import TestClient

from main import app
from services.horizon_and_ops_service import compute_operational_windows

client = TestClient(app)


def test_compute_operational_windows_uses_real_horizons_and_computes_vertical_array_gain():
    ops = compute_operational_windows(antenna_height_m=6.0, los_margin_deg=0.25, step_hours=6)
    hd = ops["horizon_dynamics"]
    assert hd["source"] == "jpl_horizons_recorded_fixture"
    assert len(hd["skyplot_samples"]) == 9
    assert hd["sun_elevation_min_deg"] == 1.506
    assert hd["earth_elevation_min_deg"] == -4.022
    assert hd["countdown_to_sunset_hours"] is None
    assert "No sunset within the 48.0h" in hd["sunset_status"]
    assert hd["countdown_to_earthrise_hours"] is None
    power = hd["solar_array_power_assessment"]
    assert power["vertical_vs_horizontal_flux_multiplier"] > 35.0
    assert power["vertical_tracking_array_mean_cosine"] > 0.99


def test_schedule_slip_and_multi_program_comparator():
    ops = compute_operational_windows(antenna_height_m=6.0, los_margin_deg=0.25, step_hours=6)
    delays = ops["schedule_slip_sensitivity"]["in_window_delays"]
    assert [d["delay_hours"] for d in delays] == [0, 12, 24, 36]
    # Earth is rising during the Nov 14-16 window, so T+36h has higher Earth elevation than T+0h
    assert delays[-1]["initial_earth_elevation_deg"] > delays[0]["initial_earth_elevation_deg"]
    programs = ops["programs"]
    assert len(programs) >= 7
    agencies = " ".join(p["agency"] for p in programs)
    assert "NASA" in agencies and "CSA" in agencies and "ISRO" in agencies
    assert set(ops["audience_modes"]) == {"mission_planner", "educator_public"}


def test_horizon_ops_endpoint_and_reference_kpis_enrichment():
    res = client.get("/api/v1/mission/horizon-ops?antenna_height_m=6.0&los_margin_deg=0.25&step_hours=6")
    assert res.status_code == 200
    body = res.json()
    assert body["service"] == "horizon_and_operational_windows"
    assert len(body["horizon_dynamics"]["skyplot_samples"]) == 9

    sim = client.post("/api/v1/simulation/run", json={
        "site_id": "shackleton",
        "lat": -89.9,
        "lon": 0.0,
        "start_time": "2026-11-14T12:00:00Z",
        "mission_duration_days": 2,
        "timestep_hours": 6,
        "antenna_height_m": 6.0,
        "los_margin_deg": 0.25,
        "demo_mode": False,
    }).json()
    ref = sim["reference_kpis"]
    assert ref["vertical_array_cosine_factor"] > 0.99
    assert ref["horizontal_surface_sine_factor"] < 0.05
    assert "sunset_countdown_status" in ref
    assert "earthset_countdown_status" in ref
