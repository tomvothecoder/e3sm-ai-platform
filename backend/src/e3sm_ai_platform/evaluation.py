"""Synchronous E3SM Compass evaluator adapter."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from e3sm_ai_platform.application.service import CompassService
from e3sm_ai_platform.domain.models import QueryRequest


@lru_cache(maxsize=1)
def _service() -> CompassService:
    """Return the evaluator's cached application service without HTTP wiring."""
    return CompassService()


def evaluate(question: str) -> dict[str, Any]:
    """Return the stable E3SM Compass evaluator mapping contract."""
    response = _service().query(QueryRequest(question=question, top_k=6, include_evidence=True))
    evidence = [item.model_dump(mode="json") for item in response.retrieved_evidence]

    return {
        "answer": response.answer,
        "route": response.route.value,
        "retrieved_evidence": evidence,
        "citations": [item.model_dump(mode="json") for item in response.citations],
        "insufficient_evidence": response.insufficient_evidence,
    }
