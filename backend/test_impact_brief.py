from fastapi.testclient import TestClient

from main import app
from services.impact_brief_service import build_decision_brief

client = TestClient(app)


def test_decision_brief_is_ranked_and_discloses_scope():
    brief = build_decision_brief()
    assert brief["status"] == "reference_triage_only"
    assert len(brief["ranked_regions"]) == 5
    scores = [row["triage_index"] for row in brief["ranked_regions"]]
    assert scores == sorted(scores, reverse=True)
    assert "not DTE availability" in " ".join(brief["ranked_regions"][0]["blockers"])
    assert brief["provenance"]["raster_products"] == 336
    assert brief["recommended_work_packages"][0]["priority"] == 1


def test_decision_brief_endpoint_exposes_actionable_work_packages():
    response = client.get("/api/v1/mission/decision-brief")
    assert response.status_code == 200
    data = response.json()
    assert data["brief_type"] == "evidence_first_mission_triage"
    assert data["ranked_regions"][0]["rank"] == 1
    assert len(data["recommended_work_packages"]) >= 4
    assert any("DEM" in item["action"] for item in data["recommended_work_packages"])
    assert any("not a landing certificate" in limitation for limitation in data["limitations"])
