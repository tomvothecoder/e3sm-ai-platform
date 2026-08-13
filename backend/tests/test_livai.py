import json
from collections.abc import Iterator

import httpx
import pytest

from e3sm_assist.app import AssistService
from e3sm_assist.livai import (
    MAX_EVIDENCE_PROMPT_CHARS,
    LivAIChatClient,
    LivAIEvidenceGenerator,
    LivAIProviderError,
    build_generator,
    build_livai_messages,
)
from e3sm_assist.models import Evidence, QueryRequest, RouteName, SourceMetadata
from e3sm_assist.settings import (
    DEFAULT_LIVAI_BASE_URL,
    DEFAULT_LIVAI_MODEL,
    Settings,
    load_settings,
)


class FakeChatClient:
    def __init__(
        self,
        response: str = "LLM answer from cited evidence.",
        fail: bool = False,
    ) -> None:
        self.response = response
        self.fail = fail
        self.messages: list[dict[str, str]] | None = None

    def complete(self, messages: list[dict[str, str]]) -> str:
        self.messages = messages
        if self.fail:
            raise RuntimeError("boom")
        return self.response


@pytest.fixture
def clear_livai_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    for key in [
        "ASSISTANT_GENERATOR",
        "ASSISTANT_LIVAI_API_KEY",
        "ASSISTANT_LIVAI_MODEL",
        "ASSISTANT_LIVAI_BASE_URL",
        "E3SM_ASSIST_CORS_ALLOW_ORIGINS",
    ]:
        monkeypatch.delenv(key, raising=False)
    yield


def _evidence() -> list[Evidence]:
    source = SourceMetadata.model_validate(
        {
            "source_id": "user-guide:compsets",
            "title": "E3SM User Guide: Compsets",
            "url": "https://docs.e3sm.org/E3SM/user-guide/compsets/",
            "section": "Compsets",
            "component": "User Guide",
            "version": "latest",
            "authority": "official",
            "provenance": "official test source",
        }
    )
    return [
        Evidence(
            chunk_id="user-guide:compsets#chunk-1",
            text="Compsets define active, data, stub, or prescribed components.",
            score=0.5,
            source=source,
            matched_terms=["compsets"],
            coverage=0.5,
        )
    ]


def test_settings_defaults_and_enablement(clear_livai_env: None) -> None:
    settings = load_settings(load_dotenv_file=False)

    assert settings.assistant_generator == "deterministic"
    assert settings.livai_model == DEFAULT_LIVAI_MODEL
    assert settings.livai_base_url == DEFAULT_LIVAI_BASE_URL
    assert settings.livai_enabled is False
    assert settings.cors_allow_origins == ("http://localhost:5173",)


def test_livai_enablement_requires_flag_and_key(
    clear_livai_env: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ASSISTANT_GENERATOR", "livai")
    assert build_generator(load_settings(load_dotenv_file=False)) is None

    monkeypatch.setenv("ASSISTANT_LIVAI_API_KEY", "test-key")
    generator = build_generator(load_settings(load_dotenv_file=False))

    assert generator is not None


def test_livai_prompt_contains_question_evidence_and_constraints() -> None:
    messages = build_livai_messages("How choose compsets?", _evidence())

    assert "Answer only from the provided E3SM evidence" in messages[0]["content"]
    assert "Do not add claims beyond the sources" in messages[0]["content"]
    assert "How choose compsets?" in messages[1]["content"]
    assert "user-guide:compsets" in messages[1]["content"]
    assert "Compsets define" in messages[1]["content"]


def test_livai_prompt_context_is_deterministically_bounded() -> None:
    evidence = _evidence()
    evidence[0].text = "x" * (MAX_EVIDENCE_PROMPT_CHARS * 2)

    messages = build_livai_messages("How choose compsets?", evidence)

    user_content = messages[1]["content"]
    assert len(user_content) < MAX_EVIDENCE_PROMPT_CHARS + 200
    assert "Evidence context truncated deterministically" in user_content


def test_livai_http_client_sends_expected_url_header_and_payload() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["authorization"] = request.headers["Authorization"]
        captured["payload"] = json.loads(request.content.decode())
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "answer"}}]},
        )

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = LivAIChatClient(
        api_key="secret-key",
        model="gpt-5.5",
        base_url="https://livai-api.llnl.gov/",
        http_client=http_client,
    )

    assert client.complete([{"role": "user", "content": "hello"}]) == "answer"
    assert captured["url"] == "https://livai-api.llnl.gov/v1/chat/completions"
    assert captured["authorization"] == "Bearer secret-key"
    payload = captured["payload"]
    assert isinstance(payload, dict)
    assert payload["model"] == "gpt-5.5"
    assert payload["messages"] == [{"role": "user", "content": "hello"}]
    assert payload["temperature"] == 0


def test_livai_rejects_non_https_base_url_before_sending_credential() -> None:
    called = False

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal called
        called = True
        return httpx.Response(200, json={"choices": [{"message": {"content": "answer"}}]})

    with pytest.raises(LivAIProviderError, match="invalid_https_base_url"):
        LivAIChatClient(
            api_key="secret-key",
            model="gpt-5.5",
            base_url="http://livai-api.llnl.gov/",
            http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        )

    assert called is False


@pytest.mark.parametrize(
    ("response", "expected_code"),
    [
        (httpx.Response(500, json={"error": "nope"}), "http_status_500"),
        (httpx.Response(200, json={}), "missing_choices"),
        (httpx.Response(200, json={"choices": []}), "missing_choices"),
        (httpx.Response(200, json={"choices": [{"message": {}}]}), "empty_content"),
    ],
)
def test_livai_response_validation_error_mapping(
    response: httpx.Response,
    expected_code: str,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return response

    client = LivAIChatClient(
        api_key="secret-key",
        model="gpt-5.5",
        base_url="https://livai-api.llnl.gov/",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    with pytest.raises(LivAIProviderError) as exc_info:
        client.complete([{"role": "user", "content": "hello"}])

    assert exc_info.value.code == expected_code


def test_livai_generator_preserves_server_citations_and_evidence() -> None:
    fake_client = FakeChatClient("Compsets select component configurations from the evidence.")
    generator = LivAIEvidenceGenerator(fake_client)

    response = generator("How choose compsets?", RouteName.CURATED_RAG, _evidence(), True, "test")

    assert response.answer.startswith("Compsets select component configurations")
    assert response.citations[0].source_id == "user-guide:compsets"
    assert response.retrieved_evidence[0].source_id == "user-guide:compsets"
    assert response.evidence[0].chunk_id == "user-guide:compsets#chunk-1"
    assert response.debug["livai_used"] is True
    assert fake_client.messages is not None


def test_livai_failure_falls_back_to_deterministic_cited_answer() -> None:
    generator = LivAIEvidenceGenerator(FakeChatClient(fail=True))

    response = generator("How choose compsets?", RouteName.CURATED_RAG, _evidence(), True, "test")

    assert "Based on the curated E3SM evidence" in response.answer
    assert response.citations[0].source_id == "user-guide:compsets"
    assert response.retrieved_evidence[0].source_id == "user-guide:compsets"
    assert response.debug["livai_fallback"] is True
    assert response.debug["livai_error"] == "RuntimeError"


def test_livai_fallback_debug_never_exposes_secret_or_endpoint() -> None:
    class SecretFailureClient:
        def complete(self, messages: list[dict[str, str]]) -> str:
            raise RuntimeError(
                "secret-key https://livai-api.llnl.gov/ Authorization: Bearer secret-key"
            )

    generator = LivAIEvidenceGenerator(SecretFailureClient())

    response = generator("How choose compsets?", RouteName.CURATED_RAG, _evidence(), True, "test")
    public_debug = json.dumps(response.debug, sort_keys=True)

    assert "secret-key" not in public_debug
    assert "livai-api.llnl.gov" not in public_debug
    assert "Authorization" not in public_debug


def test_service_uses_deterministic_default_without_livai_key(clear_livai_env: None) -> None:
    service = AssistService(settings=Settings(assistant_generator="livai", livai_api_key=None))

    response = service.query(QueryRequest(question="How do I choose an E3SM compset?"))

    assert "Based on the curated E3SM evidence" in response.answer
    assert "livai_used" not in response.debug
