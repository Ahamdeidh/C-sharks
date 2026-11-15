from fastapi.testclient import TestClient

from main import app
from services.mission_design_lab_service import build_design_lab

client = TestClient(app)


def test_design_lab_has_counterfactual_modes_and_explainable_contributions():
    lab = build_design_lab()
    assert lab["lab_type"] == "counterfactual_mission_design_lab"
    assert {scenario["mode_id"] for scenario in lab["scenarios"]} == {"balanced", "solar_first", "communications_first", "science_first"}
    assert all(len(scenario["ranked_regions"]) == 5 for scenario in lab["scenarios"])
    assert all("contribution" in scenario["ranked_regions"][0] for scenario in lab["scenarios"])
    assert any(scenario["ranked_regions"][0]["name"] != lab["scenarios"][0]["ranked_regions"][0]["name"] for scenario in lab["scenarios"][1:])
    assert any("not verified DTE" in limitation for limitation in lab["limitations"])


def test_design_lab_endpoint():
    response = client.get("/api/v1/mission/design-lab")
    assert response.status_code == 200
    assert response.json()["scenarios"][0]["creative_question"]
