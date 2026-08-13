"""Pytest fixtures for the external E3SM-ASSIST evaluation contract."""

from __future__ import annotations

import importlib
import os
from collections.abc import Callable, Mapping
from typing import cast

import pytest

from evaluation.dataset import load_cases


@pytest.fixture(scope="session")
def evaluation_cases() -> list[dict[str, object]]:
    return load_cases()


@pytest.fixture(scope="session")
def evaluate() -> Callable[[str], Mapping[str, object]]:
    """Load the configured backend evaluator exactly once per pytest session."""
    target = os.getenv("E3SM_ASSIST_EVALUATOR")
    if not target:
        pytest.skip("Set E3SM_ASSIST_EVALUATOR=package.module:callable to run integration evaluation")

    try:
        module_name, callable_name = target.split(":", 1)
        evaluator = getattr(importlib.import_module(module_name), callable_name)
    except (ImportError, AttributeError, ValueError) as exc:
        pytest.fail(f"Unable to load E3SM_ASSIST_EVALUATOR={target!r}: {exc}")

    if not callable(evaluator):
        pytest.fail("E3SM_ASSIST_EVALUATOR must name a callable accepting one question string")
    return cast(Callable[[str], Mapping[str, object]], evaluator)


@pytest.fixture(scope="session")
def results_by_id(evaluate: Callable[[str], Mapping[str, object]], evaluation_cases: list[dict[str, object]]) -> dict[str, Mapping[str, object]]:
    """Evaluate every prompt once, avoiding repeated backend initialization or calls."""
    results: dict[str, Mapping[str, object]] = {}
    for case in evaluation_cases:
        result = evaluate(str(case["question"]))
        assert isinstance(result, Mapping), f"{case['id']}: evaluator must return a mapping"
        results[str(case["id"])] = result
    return results
