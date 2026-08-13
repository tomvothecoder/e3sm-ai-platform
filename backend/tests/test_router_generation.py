from pydantic import HttpUrl, TypeAdapter

from e3sm_assist.generation import generate_response
from e3sm_assist.models import Evidence, RouteName, SourceMetadata
from e3sm_assist.router import DeterministicRouter

_HTTP_URL_ADAPTER: TypeAdapter[HttpUrl] = TypeAdapter(HttpUrl)


def _evidence(score: float = 0.4) -> list[Evidence]:
    source = SourceMetadata(
        source_id="running-guide:run-and-submit",
        title="Running E3SM: case.submit",
        url=_HTTP_URL_ADAPTER.validate_python(
            "https://docs.e3sm.org/E3SM/user-guide/running-e3sm/case-submit/"
        ),
        section="Submit",
        component="Running E3SM",
        version="latest",
        authority="official",
        provenance="test",
    )
    return [
        Evidence(
            chunk_id="running-guide:run-and-submit#chunk-1",
            text="case.submit submits the model run.",
            score=score,
            source=source,
        )
    ]


def test_router_selects_curated_rag_with_sufficient_evidence() -> None:
    decision = DeterministicRouter().route("How do I submit a case?", _evidence())

    assert decision.route is RouteName.CURATED_RAG


def test_router_selects_web_for_current_questions() -> None:
    decision = DeterministicRouter().route("What is the latest E3SM release today?", _evidence())

    assert decision.route is RouteName.WEB_SEARCH


def test_router_selects_operational_tool_for_live_status() -> None:
    decision = DeterministicRouter().route("What is my case status in the queue?", _evidence())

    assert decision.route is RouteName.OPERATIONAL_TOOL


def test_router_selects_insufficient_when_no_evidence() -> None:
    decision = DeterministicRouter().route("Explain unrelated astrophysics", [])

    assert decision.route is RouteName.INSUFFICIENT_EVIDENCE


def test_generation_for_curated_answer_has_citations_and_caveat() -> None:
    response = generate_response(
        "How submit?",
        RouteName.CURATED_RAG,
        _evidence(),
        True,
        "test reason",
    )

    assert response.insufficient_evidence is False
    assert response.route.value == "curated"
    assert response.citations[0].source_id == "running-guide:run-and-submit"
    assert response.retrieved_evidence[0].source_id == response.citations[0].source_id
    assert "not added claims beyond" in response.answer


def test_generation_for_external_routes_is_explicitly_insufficient() -> None:
    response = generate_response("latest?", RouteName.WEB_SEARCH, _evidence(), False, "current")

    assert response.insufficient_evidence is True
    assert response.citations == []
    assert response.evidence == []
    assert response.retrieved_evidence == []
    assert "no live web-search provider" in response.answer


def test_router_prefers_operational_pull_request_over_recency() -> None:
    decision = DeterministicRouter().route(
        "Which open pull requests currently modify EAMxx configuration files?",
        _evidence(),
    )

    assert decision.route is RouteName.OPERATIONAL_TOOL


def test_router_does_not_match_pr_inside_ordinary_words() -> None:
    for question in [
        "Which E3SM docs represent atmosphere configuration options?",
        "What does E3SM-Unified provide for building the E3SM software stack?",
    ]:
        decision = DeterministicRouter().route(question, _evidence())

        assert decision.route is RouteName.CURATED_RAG


def test_router_detects_upcoming_workshop_as_web() -> None:
    decision = DeterministicRouter().route("When is the next E3SM community workshop?", [])

    assert decision.route is RouteName.WEB_SEARCH
