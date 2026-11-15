from fastapi.testclient import TestClient

from main import app
from services.scientific_validation_service import build_validation_report

client = TestClient(app)
BASE = {"site_id": "shackleton", "lat": -89.9, "lon": 0.0, "start_time": "2026-11-14T12:00:00Z", "mission_duration_days": 1, "timestep_hours": 12, "antenna_height_m": 6.0, "los_margin_deg": 0.25}


def test_demo_validation_blocks_synthetic_and_terrain_claims():
    report = build_validation_report(ephemeris_check=None, demo_mode=True, total_steps=2, timeline_length=2)
    assert report["status"] == "blocked"
    assert any(check["id"] == "synthetic_kpis" and check["status"] == "blocked" for check in report["checks"])
    assert any(check["id"] == "terrain_pipeline" and check["status"] == "blocked" for check in report["checks"])


def test_simulation_response_contains_validation_report():
    response = client.post("/api/v1/simulation/run", json={**BASE, "demo_mode": True})
    assert response.status_code == 200
    report = response.json()["validation_report"]
    assert report["meaning"].startswith("A quality gate")
    assert report["checks"]
    assert any("LOLA" in item for item in report["required_for_real_engine"])
