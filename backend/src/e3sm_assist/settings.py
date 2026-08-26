"""Backend settings loaded from environment and optional local .env."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

DEFAULT_LIVAI_BASE_URL = "https://livai-api.llnl.gov/"
DEFAULT_LIVAI_MODEL = "gpt-5.5"
DEFAULT_EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
RETRIEVAL_MODES = frozenset({"lexical", "semantic", "hybrid"})


@dataclass(frozen=True)
class Settings:
    """Runtime settings for provider selection and local prototype access."""

    assistant_generator: str = "deterministic"
    livai_api_key: str | None = None
    livai_model: str = DEFAULT_LIVAI_MODEL
    livai_base_url: str = DEFAULT_LIVAI_BASE_URL
    cors_allow_origins: tuple[str, ...] = ("http://localhost:5173",)
    service_name: str = "e3sm-assist"
    deployment_environment: str = "development"
    otlp_endpoint: str | None = None
    otlp_headers: tuple[tuple[str, str], ...] = ()
    retrieval_mode: str = "lexical"
    embedding_model: str = DEFAULT_EMBEDDING_MODEL
    retrieval_lexical_min_coverage: float = 0.18
    retrieval_lexical_min_score: float = 0.11
    retrieval_semantic_min_score: float = 0.7
    retrieval_lexical_weight: float = 0.5
    retrieval_semantic_weight: float = 0.5

    def __post_init__(self) -> None:
        """Validate retrieval configuration independently of environment loading."""
        if self.retrieval_mode not in RETRIEVAL_MODES:
            modes = ", ".join(sorted(RETRIEVAL_MODES))
            raise ValueError(f"retrieval_mode must be one of: {modes}")
        if not self.embedding_model.strip():
            raise ValueError("embedding_model must not be empty")
        if not 0.0 <= self.retrieval_lexical_min_coverage <= 1.0:
            raise ValueError("retrieval_lexical_min_coverage must be between 0 and 1")
        if self.retrieval_lexical_min_score < 0.0:
            raise ValueError("retrieval_lexical_min_score must be non-negative")
        if not -1.0 <= self.retrieval_semantic_min_score <= 1.0:
            raise ValueError("retrieval_semantic_min_score must be between -1 and 1")
        if self.retrieval_lexical_weight < 0.0 or self.retrieval_semantic_weight < 0.0:
            raise ValueError("retrieval weights must be non-negative")
        if self.retrieval_lexical_weight + self.retrieval_semantic_weight == 0.0:
            raise ValueError("at least one retrieval weight must be positive")

    @property
    def livai_enabled(self) -> bool:
        """LivAI is explicitly enabled only when requested and a key is present."""
        return self.assistant_generator.lower() == "livai" and bool(self.livai_api_key)


def load_settings(load_dotenv_file: bool = True) -> Settings:
    """Load settings from environment, optionally reading backend/.env if present."""
    if load_dotenv_file:
        load_dotenv(Path(__file__).parents[2] / ".env", override=False)

    raw_origins = os.getenv("E3SM_ASSIST_CORS_ALLOW_ORIGINS", "http://localhost:5173")
    origins = tuple(origin.strip() for origin in raw_origins.split(",") if origin.strip())
    raw_headers = os.getenv("E3SM_ASSIST_OTLP_HEADERS", "")
    headers = tuple(
        (name.strip(), value.strip())
        for item in raw_headers.split(",")
        if "=" in item
        for name, value in [item.split("=", maxsplit=1)]
        if name.strip() and value.strip()
    )
    return Settings(
        assistant_generator=os.getenv("ASSISTANT_GENERATOR", "deterministic"),
        livai_api_key=os.getenv("ASSISTANT_LIVAI_API_KEY") or None,
        livai_model=os.getenv("ASSISTANT_LIVAI_MODEL", DEFAULT_LIVAI_MODEL),
        livai_base_url=os.getenv("ASSISTANT_LIVAI_BASE_URL", DEFAULT_LIVAI_BASE_URL),
        cors_allow_origins=origins or ("http://localhost:5173",),
        service_name=os.getenv("E3SM_ASSIST_SERVICE_NAME", "e3sm-assist"),
        deployment_environment=os.getenv("E3SM_ASSIST_DEPLOYMENT_ENVIRONMENT", "development"),
        otlp_endpoint=os.getenv("E3SM_ASSIST_OTLP_ENDPOINT") or None,
        otlp_headers=headers,
        retrieval_mode=os.getenv("E3SM_ASSIST_RETRIEVAL_MODE", "lexical").lower(),
        embedding_model=os.getenv("E3SM_ASSIST_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL),
        retrieval_lexical_min_coverage=float(
            os.getenv("E3SM_ASSIST_RETRIEVAL_LEXICAL_MIN_COVERAGE", "0.18")
        ),
        retrieval_lexical_min_score=float(
            os.getenv("E3SM_ASSIST_RETRIEVAL_LEXICAL_MIN_SCORE", "0.11")
        ),
        retrieval_semantic_min_score=float(
            os.getenv("E3SM_ASSIST_RETRIEVAL_SEMANTIC_MIN_SCORE", "0.7")
        ),
        retrieval_lexical_weight=float(os.getenv("E3SM_ASSIST_RETRIEVAL_LEXICAL_WEIGHT", "0.5")),
        retrieval_semantic_weight=float(os.getenv("E3SM_ASSIST_RETRIEVAL_SEMANTIC_WEIGHT", "0.5")),
    )
