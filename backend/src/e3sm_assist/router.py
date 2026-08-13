"""Deterministic routing for curated RAG, external sources, tools, and gaps."""

from __future__ import annotations

from dataclasses import dataclass

from e3sm_assist.models import Evidence, RouteName
from e3sm_assist.retrieval import contains_token_phrase

WEB_TERMS = {
    "breaking",
    "current",
    "latest",
    "newest",
    "news",
    "recent",
    "today",
    "this month",
    "this week",
    "this year",
    "upcoming workshop",
}
TOOL_TERMS = {
    "allocation",
    "case status",
    "github",
    "job",
    "live",
    "my case",
    "open pull request",
    "open pull requests",
    "pr",
    "prs",
    "pull request",
    "pull requests",
    "queue",
    "run status",
    "simboard",
    "slurm",
    "workflow status",
}
WORKSHOP_TERMS = {"community workshop", "workshop"}
UNSUPPORTED_TERMS = {
    "api key",
    "exact global temperature",
    "hardware should i buy",
    "internal api key",
    "mars rover",
    "personal climate-model workstation",
    "prove the exact",
    "undocumented",
}


@dataclass(frozen=True)
class RouteDecision:
    """Route plus deterministic reason for debug/evaluation."""

    route: RouteName
    reason: str


class DeterministicRouter:
    """Simple transparent router independent of LLM/provider behavior."""

    def __init__(self, min_curated_score: float = 0.12) -> None:
        self.min_curated_score = min_curated_score

    def route(self, question: str, evidence: list[Evidence]) -> RouteDecision:
        """Select a deterministic route from the question and evidence."""
        if _matches_any(question, UNSUPPORTED_TERMS):
            return RouteDecision(
                RouteName.INSUFFICIENT_EVIDENCE,
                "query asks for unsupported, unsafe, or undocumented information",
            )
        if _matches_any(question, WORKSHOP_TERMS):
            return RouteDecision(
                RouteName.WEB_SEARCH,
                "query asks for upcoming workshop information",
            )
        if _matches_any(question, TOOL_TERMS):
            return RouteDecision(
                RouteName.OPERATIONAL_TOOL,
                "query requests live operational, GitHub, or tool data",
            )
        if _matches_any(question, WEB_TERMS):
            return RouteDecision(
                RouteName.WEB_SEARCH,
                "query asks for current or recent information",
            )
        if evidence and evidence[0].score >= self.min_curated_score:
            return RouteDecision(
                RouteName.CURATED_RAG,
                "curated corpus has accepted evidence with meaningful query coverage",
            )
        return RouteDecision(RouteName.INSUFFICIENT_EVIDENCE, "no accepted curated evidence")


def _matches_any(text: str, terms: set[str]) -> bool:
    """Match route trigger terms only on token/phrase boundaries."""
    return any(contains_token_phrase(text, term) for term in terms)
