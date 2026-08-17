import pytest

from e3sm_assist.settings import DEFAULT_EMBEDDING_MODEL, Settings, load_settings


def test_retrieval_settings_default_to_offline_safe_lexical_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in [
        "E3SM_ASSIST_RETRIEVAL_MODE",
        "E3SM_ASSIST_EMBEDDING_MODEL",
        "E3SM_ASSIST_RETRIEVAL_LEXICAL_MIN_COVERAGE",
        "E3SM_ASSIST_RETRIEVAL_LEXICAL_MIN_SCORE",
        "E3SM_ASSIST_RETRIEVAL_SEMANTIC_MIN_SCORE",
        "E3SM_ASSIST_RETRIEVAL_LEXICAL_WEIGHT",
        "E3SM_ASSIST_RETRIEVAL_SEMANTIC_WEIGHT",
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
    monkeypatch.setenv("E3SM_ASSIST_RETRIEVAL_MODE", "hybrid")
    monkeypatch.setenv("E3SM_ASSIST_EMBEDDING_MODEL", "example/technical-model")
    monkeypatch.setenv("E3SM_ASSIST_RETRIEVAL_SEMANTIC_MIN_SCORE", "0.82")
    monkeypatch.setenv("E3SM_ASSIST_RETRIEVAL_LEXICAL_WEIGHT", "0.3")
    monkeypatch.setenv("E3SM_ASSIST_RETRIEVAL_SEMANTIC_WEIGHT", "0.7")

    settings = load_settings(load_dotenv_file=False)

    assert settings.retrieval_mode == "hybrid"
    assert settings.embedding_model == "example/technical-model"
    assert settings.retrieval_semantic_min_score == 0.82
    assert settings.retrieval_lexical_weight == 0.3
    assert settings.retrieval_semantic_weight == 0.7


def test_retrieval_settings_reject_invalid_mode() -> None:
    with pytest.raises(ValueError, match="retrieval_mode"):
        Settings(retrieval_mode="unknown")
