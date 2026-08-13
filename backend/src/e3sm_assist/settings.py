"""Backend settings loaded from environment and optional local .env."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

DEFAULT_LIVAI_BASE_URL = "https://livai-api.llnl.gov/"
DEFAULT_LIVAI_MODEL = "gpt-5.5"


@dataclass(frozen=True)
class Settings:
    """Runtime settings for provider selection and local prototype access."""

    assistant_generator: str = "deterministic"
    livai_api_key: str | None = None
    livai_model: str = DEFAULT_LIVAI_MODEL
    livai_base_url: str = DEFAULT_LIVAI_BASE_URL
    cors_allow_origins: tuple[str, ...] = ("http://localhost:5173",)

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
    return Settings(
        assistant_generator=os.getenv("ASSISTANT_GENERATOR", "deterministic"),
        livai_api_key=os.getenv("ASSISTANT_LIVAI_API_KEY") or None,
        livai_model=os.getenv("ASSISTANT_LIVAI_MODEL", DEFAULT_LIVAI_MODEL),
        livai_base_url=os.getenv("ASSISTANT_LIVAI_BASE_URL", DEFAULT_LIVAI_BASE_URL),
        cors_allow_origins=origins or ("http://localhost:5173",),
    )
