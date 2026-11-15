from fastapi.testclient import TestClient

from main import app
from services.judge_evidence_service import build_judge_evidence_pack

client = TestClient(app)


def test_evidence_pack_connects_all_four_scored_criteria():
    pack = build_judge_evidence_pack()
    assert pack["pack_type"] == "judge_evidence_pack"
    assert len(pack["walkthrough"]) == 5
    assert set(pack["score_support"]) == {"impact", "creativity", "validity", "relevance"}
    assert any("counterfactual" in step["answer"].lower() for step in pack["walkthrough"])
    assert any("benchmarks" in step["answer"] for step in pack["walkthrough"])


def test_evidence_pack_endpoint_is_reviewer_ready():
    response = client.get("/api/v1/judge/evidence-pack")
    assert response.status_code == 200
    data = response.json()
    assert data["walkthrough"][0]["evidence"]
    assert data["limitations"]
