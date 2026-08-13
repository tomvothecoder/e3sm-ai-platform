"""Deterministic black-box checks for the E3SM-ASSIST response contract."""

from __future__ import annotations

from collections.abc import Mapping

import pytest

from evaluation.dataset import load_cases

CASES = load_cases()
CASES_REQUIRING_CITATIONS = [case for case in CASES if case["requires_citations"]]
CASES_REQUIRING_INSUFFICIENT_EVIDENCE = [
    case for case in CASES if case.get("requires_insufficient_evidence", False)
]


def _records(result: Mapping[str, object], field: str) -> list[Mapping[str, object]]:
    records = result.get(field, [])
    assert isinstance(records, list), f"{field} must be a list"
    assert all(isinstance(record, Mapping) for record in records), f"{field} entries must be mappings"
    return records  # type: ignore[return-value]


@pytest.mark.parametrize("case", CASES, ids=lambda case: str(case["id"]))
def test_route_and_retrieval_contract(results_by_id, case):
    result = results_by_id[case["id"]]
    assert result.get("route") == case["expected_route"], case["id"]

    expected_sources = set(case["expected_source_ids"])
    if expected_sources:
        evidence_sources = {record.get("source_id") for record in _records(result, "retrieved_evidence")}
        assert expected_sources <= evidence_sources, f"{case['id']}: expected relevant curated source(s)"


@pytest.mark.parametrize("case", CASES_REQUIRING_CITATIONS, ids=lambda case: str(case["id"]))
def test_curated_answers_include_citation_provenance(results_by_id, case):
    citations = _records(results_by_id[case["id"]], "citations")
    assert citations, f"{case['id']}: curated answer needs citations"
    assert all(citation.get("source_id") and citation.get("provenance") for citation in citations), case["id"]


@pytest.mark.parametrize(
    "case",
    CASES_REQUIRING_INSUFFICIENT_EVIDENCE,
    ids=lambda case: str(case["id"]),
)
def test_insufficient_evidence_is_explicit(results_by_id, case):
    result = results_by_id[case["id"]]
    assert result.get("insufficient_evidence") is True, case["id"]
    assert _records(result, "retrieved_evidence") == [], case["id"]
    answer = result.get("answer", "")
    assert isinstance(answer, str) and "insufficient" in answer.lower(), case["id"]
