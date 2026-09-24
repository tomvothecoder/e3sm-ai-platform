from pathlib import Path

import pytest

from e3sm_ai_platform.infrastructure.settings import (
    DEFAULT_EMBEDDING_MODEL,
    ENV_FILE,
    Settings,
    load_settings,
)


def test_environment_file_is_loaded_from_the_backend_root() -> None:
    assert ENV_FILE == Path(__file__).parents[1] / ".env"


def test_retrieval_settings_default_to_offline_safe_lexical_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in [
        "RETRIEVAL_MODE",
        "EMBEDDING_MODEL",
        "RETRIEVAL_LEXICAL_MIN_COVERAGE",
        "RETRIEVAL_LEXICAL_MIN_SCORE",
        "RETRIEVAL_SEMANTIC_MIN_SCORE",
        "RETRIEVAL_LEXICAL_WEIGHT",
        "RETRIEVAL_SEMANTIC_WEIGHT",
    ]:
        monkeypatch.delenv(name, raising=False)

    settings = load_settings(load_dotenv_file=False)

    assert settings.retrieval_mode == "lexical"
    assert settings.embedding_model == DEFAULT_EMBEDDING_MODEL
    assert settings.retrieval_lexical_min_coverage == 0.18
    assert settings.retrieval_lexical_min_score == 0.11
    assert settings.retrieval_semantic_min_score == 0.7
    assert settings.retrieval_lexical_weight == 0.5
    assert settings.retrieval_semantic_weight == 0.5


def test_retrieval_settings_load_semantic_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RETRIEVAL_MODE", "hybrid")
    monkeypatch.setenv("EMBEDDING_MODEL", "example/technical-model")
    monkeypatch.setenv("RETRIEVAL_SEMANTIC_MIN_SCORE", "0.82")
    monkeypatch.setenv("RETRIEVAL_LEXICAL_WEIGHT", "0.3")
    monkeypatch.setenv("RETRIEVAL_SEMANTIC_WEIGHT", "0.7")

    settings = load_settings(load_dotenv_file=False)

    assert settings.retrieval_mode == "hybrid"
    assert settings.embedding_model == "example/technical-model"
    assert settings.retrieval_semantic_min_score == 0.82
    assert settings.retrieval_lexical_weight == 0.3
    assert settings.retrieval_semantic_weight == 0.7


def test_retrieval_settings_reject_invalid_mode() -> None:
    with pytest.raises(ValueError, match="retrieval_mode"):
        Settings(retrieval_mode="unknown")
