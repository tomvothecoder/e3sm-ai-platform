from fastapi.testclient import TestClient

from e3sm_assist.app import app

client = TestClient(app)


def test_health_reports_corpus() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert 20 <= body["corpus"]["entries"] <= 50
    assert body["chunks"] >= body["corpus"]["entries"]


def test_query_returns_curated_answer_with_citations_and_evidence() -> None:
    response = client.post("/query", json={"question": "How do I submit an E3SM case?", "top_k": 3})

    assert response.status_code == 200
    body = response.json()
    assert body["route"] == "curated"
    assert body["route_alias"] == "curated_rag"
    assert body["insufficient_evidence"] is False
    assert body["citations"]
    assert body["citations"][0]["url"].startswith("https://docs.e3sm.org/")
    assert body["evidence"]
    assert body["retrieved_evidence"]
    assert body["retrieved_evidence"][0]["source_id"] == body["evidence"][0]["source"]["source_id"]
    assert body["evidence"][0]["source"]["provenance"]


def test_query_can_hide_evidence() -> None:
    response = client.post(
        "/query",
        json={"question": "How do EAMxx diagnostics work?", "top_k": 2, "include_evidence": False},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["route"] == "curated"
    assert body["evidence"] == []
    assert body["retrieved_evidence"] == []
    assert body["citations"]


def test_query_web_route_is_insufficient_without_live_network() -> None:
    response = client.post("/query", json={"question": "What is the latest E3SM release today?"})

    assert response.status_code == 200
    body = response.json()
    assert body["route"] == "web"
    assert body["route_alias"] == "web_search"
    assert body["insufficient_evidence"] is True
    assert body["citations"] == []
    assert body["retrieved_evidence"] == []
    assert body["evidence"] == []
    assert "Insufficient curated evidence" in body["answer"]
    assert "raw_candidate_source_ids_unverified" in body["debug"]
    assert "candidate_source_ids" not in body["debug"]


def test_cors_allows_localhost_frontend_origin() -> None:
    response = client.options(
        "/query",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_query_unknown_topic_is_insufficient_evidence() -> None:
    response = client.post("/query", json={"question": "How do I tune a Mars rover battery?"})

    assert response.status_code == 200
    body = response.json()
    assert body["route"] == "insufficient_evidence"
    assert body["insufficient_evidence"] is True
    assert body["citations"] == []
    assert body["retrieved_evidence"] == []


def test_query_validation_rejects_too_short_question() -> None:
    response = client.post("/query", json={"question": "hi"})

    assert response.status_code == 422
