import json
from collections.abc import Iterator

import pytest
from pydantic_ai import Agent
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    SystemPromptPart,
    TextPart,
    UserPromptPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from e3sm_assist.app import AssistService
from e3sm_assist.livai import (
    MAX_EVIDENCE_PROMPT_CHARS,
    SYSTEM_PROMPT,
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


def _function_agent(response: str) -> Agent[None, str]:
    def complete(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        return ModelResponse(parts=[TextPart(content=response)])

    return Agent(FunctionModel(complete), output_type=str)


def test_livai_client_uses_injected_pydantic_ai_agent_without_network() -> None:
    client = LivAIChatClient(
        api_key="secret-key",
        model="gpt-5.5",
        base_url="https://livai-api.llnl.gov/",
        agent=_function_agent("answer"),
    )

    assert client.complete([{"role": "user", "content": "hello"}]) == "answer"


def test_livai_default_agent_configuration_requires_no_network() -> None:
    client = LivAIChatClient(
        api_key="secret-key",
        model="gpt-5.5",
        base_url="https://livai-api.llnl.gov/",
    )

    assert isinstance(client._agent, Agent)
    assert isinstance(client._agent.model, OpenAIChatModel)
    assert client._agent.model.model_name == "gpt-5.5"
    assert isinstance(client._agent.model.provider, OpenAIProvider)
    assert str(client._agent.model.provider.base_url) == "https://livai-api.llnl.gov/v1/"
    assert client._agent.model_settings == {"temperature": 0}


def test_livai_invocation_keeps_system_prompt_separate_from_evidence() -> None:
    captured: list[ModelMessage] = []

    def complete(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        captured.extend(messages)
        return ModelResponse(parts=[TextPart(content="answer")])

    client = LivAIChatClient(
        api_key="secret-key",
        model="gpt-5.5",
        base_url="https://livai-api.llnl.gov/",
        agent=Agent(FunctionModel(complete), system_prompt=SYSTEM_PROMPT, output_type=str),
    )
    messages = build_livai_messages("How choose compsets?", _evidence())

    assert client.complete(messages) == "answer"
    request = captured[0]
    assert isinstance(request, ModelRequest)
    system_part, user_part = request.parts[:2]
    assert isinstance(system_part, SystemPromptPart)
    assert isinstance(user_part, UserPromptPart)
    assert system_part.content == SYSTEM_PROMPT
    assert user_part.content == messages[1]["content"]
    assert SYSTEM_PROMPT not in user_part.content


def test_livai_rejects_non_https_base_url_before_sending_credential() -> None:
    with pytest.raises(LivAIProviderError, match="invalid_https_base_url"):
        LivAIChatClient(
            api_key="secret-key",
            model="gpt-5.5",
            base_url="http://livai-api.llnl.gov/",
            agent=_function_agent("answer"),
        )


def test_livai_agent_failure_is_sanitized() -> None:
    def fail(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        raise RuntimeError("secret-key https://livai-api.llnl.gov/")

    client = LivAIChatClient(
        api_key="secret-key",
        model="gpt-5.5",
        base_url="https://livai-api.llnl.gov/",
        agent=Agent(FunctionModel(fail), output_type=str),
    )

    with pytest.raises(LivAIProviderError, match="agent_run_error"):
        client.complete([{"role": "user", "content": "hello"}])


def test_livai_generator_preserves_server_citations_and_evidence() -> None:
    client = LivAIChatClient(
        api_key="test-key",
        model="test-model",
        base_url="https://livai-api.llnl.gov/",
        agent=_function_agent("Compsets select component configurations from the evidence."),
    )
    generator = LivAIEvidenceGenerator(client)

    response = generator("How choose compsets?", RouteName.CURATED_RAG, _evidence(), True, "test")

    assert response.answer.startswith("Compsets select component configurations")
    assert response.citations[0].source_id == "user-guide:compsets"
    assert response.retrieved_evidence[0].source_id == "user-guide:compsets"
    assert response.evidence[0].chunk_id == "user-guide:compsets#chunk-1"
    assert response.debug["livai_used"] is True


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
