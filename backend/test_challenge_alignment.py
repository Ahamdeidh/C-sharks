from fastapi.testclient import TestClient

from main import app
from services.challenge_alignment_service import build_challenge_alignment

client = TestClient(app)


def test_alignment_matrix_maps_goals_to_evidence_and_gaps():
    data = build_challenge_alignment()
    assert data["alignment_type"] == "challenge_traceability_matrix"
    assert len(data["criteria"]) == 4
    assert all(item["evidence"] for item in data["criteria"])
    assert any("JPL Horizons" in item["project_response"] for item in data["criteria"])
    assert data["coverage"]["criteria_with_evidence"] == 4


def test_alignment_endpoint_is_publicly_traceable():
    response = client.get("/api/v1/challenge/alignment")
    assert response.status_code == 200
    data = response.json()
    assert data["coverage"]["criteria_mapped"] == 4
    assert any(item["id"] == "nasa-data-core" for item in data["criteria"])
    assert "does not imply" in data["honesty_note"]


def test_official_challenge_metadata_and_requirement_ids():
    data = build_challenge_alignment()
    official = data["official_challenge"]
    assert official["official_title"] == "Lunar Landing Site Navigator"
    assert "spaceappschallenge.org/2026/challenges" in official["official_url"]
    objs = data["challenge_objectives_detail"]
    assert len(objs) == 7
    assert [o["requirement_id"] for o in objs] == [f"OBJ-0{i}" for i in range(1, 8)]
    assert all("code_and_endpoint" in o and "source_and_limit" in o for o in objs)
