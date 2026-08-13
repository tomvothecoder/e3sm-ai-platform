"""Evidence-constrained answer generation."""

from __future__ import annotations

from e3sm_assist.models import (
    ROUTE_ALIASES,
    Citation,
    Evidence,
    QueryResponse,
    RetrievedEvidence,
    RouteName,
)


def citations_from_evidence(evidence: list[Evidence]) -> list[Citation]:
    """Create one citation per unique source, preserving evidence rank."""

    seen: set[str] = set()
    citations: list[Citation] = []
    for item in evidence:
        if item.source.source_id in seen:
            continue
        seen.add(item.source.source_id)
        citations.append(Citation(**item.source.model_dump()))
    return citations


def flat_evidence_from_evidence(evidence: list[Evidence]) -> list[RetrievedEvidence]:
    """Flatten accepted evidence while preserving citation/source association."""

    return [
        RetrievedEvidence(
            chunk_id=item.chunk_id,
            source_id=item.source.source_id,
            title=item.source.title,
            url=item.source.url,
            section=item.source.section,
            component=item.source.component,
            provenance=item.source.provenance,
            text=item.text,
            score=item.score,
            matched_terms=item.matched_terms,
            coverage=item.coverage,
        )
        for item in evidence
    ]


def _trim_sentence(text: str, max_chars: int = 260) -> str:
    compact = " ".join(text.split())
    if len(compact) <= max_chars:
        return compact
    trimmed = compact[:max_chars].rsplit(" ", maxsplit=1)[0]
    return f"{trimmed}..."


def generate_response(
    question: str,
    route: RouteName,
    evidence: list[Evidence],
    include_evidence: bool,
    reason: str,
) -> QueryResponse:
    """Generate a deterministic answer using only retrieved evidence or a gap message."""

    if route is RouteName.CURATED_RAG and evidence:
        citations = citations_from_evidence(evidence)
        flat_evidence = flat_evidence_from_evidence(evidence) if include_evidence else []
        bullets = [
            f"- [{index}] {_trim_sentence(item.text)}"
            for index, item in enumerate(evidence, start=1)
        ]
        answer = (
            "Based on the curated E3SM evidence retrieved for this question:\n"
            + "\n".join(bullets)
            + "\n\nI have not added claims beyond these cited sources."
        )
        returned_evidence = evidence if include_evidence else []
        return QueryResponse(
            answer=answer,
            route=route,
            route_alias=ROUTE_ALIASES[route],
            citations=citations,
            evidence=returned_evidence,
            retrieved_evidence=flat_evidence,
            debug={"routing_reason": reason, "question": question},
        )

    if route is RouteName.WEB_SEARCH:
        answer = (
            "Insufficient curated evidence: this appears to require current web information, "
            "but phase 1 has no live web-search provider configured."
        )
    elif route is RouteName.OPERATIONAL_TOOL:
        answer = (
            "Insufficient evidence: this appears to require live operational/tool data, "
            "but phase 1 only exposes the provider-independent tool interface."
        )
    else:
        answer = (
            "Insufficient evidence: the curated E3SM corpus did not contain enough support "
            "to answer."
        )

    return QueryResponse(
        answer=answer,
        route=route,
        route_alias=ROUTE_ALIASES[route],
        citations=[],
        evidence=[],
        retrieved_evidence=[],
        insufficient_evidence=True,
        debug={
            "routing_reason": reason,
            "question": question,
            "candidate_count": len(evidence),
            "raw_candidate_source_ids_unverified": [item.source.source_id for item in evidence],
        },
    )
