"""Fixture loading helpers used during pytest collection and execution."""

from __future__ import annotations

import json
from pathlib import Path

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "e3sm_questions.json"


def load_cases() -> list[dict[str, object]]:
    """Return all evaluation cases in their stable fixture order."""
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return list(payload["cases"])
