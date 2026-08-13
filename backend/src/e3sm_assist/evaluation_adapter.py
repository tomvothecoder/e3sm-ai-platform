"""Packaged synchronous evaluator adapter for the independent evaluation suite."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from e3sm_assist.app import AssistService
from e3sm_assist.models import QueryRequest


@lru_cache(maxsize=1)
def _service() -> AssistService:
    return AssistService()


def evaluate(question: str) -> dict[str, Any]:
    """Return the stable E3SM_ASSIST_EVALUATOR mapping contract."""
    response = _service().query(QueryRequest(question=question, top_k=6, include_evidence=True))
    evidence = [item.model_dump(mode="json") for item in response.retrieved_evidence]
    return {
        "answer": response.answer,
        "route": response.route.value,
        "retrieved_evidence": evidence,
        "citations": [item.model_dump(mode="json") for item in response.citations],
        "insufficient_evidence": response.insufficient_evidence,
    }
