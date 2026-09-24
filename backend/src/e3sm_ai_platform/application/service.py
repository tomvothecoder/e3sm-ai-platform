"""Application service for retrieval-backed E3SM Compass responses."""

from __future__ import annotations

from typing import Protocol

from opentelemetry import trace

from e3sm_ai_platform.application.generation import generate_response
from e3sm_ai_platform.application.routing import DeterministicRouter
from e3sm_ai_platform.domain.models import Evidence, QueryRequest, QueryResponse, RouteName
from e3sm_ai_platform.infrastructure.settings import Settings, load_settings
from e3sm_ai_platform.integrations.livai import build_generator
from e3sm_ai_platform.knowledge.corpus import chunk_corpus, corpus_summary, load_corpus
from e3sm_ai_platform.knowledge.interfaces import VectorStore
from e3sm_ai_platform.knowledge.retrieval import build_retriever


class Generator(Protocol):
    """Callable interface for generating query responses."""

    def __call__(
        self,
        question: str,
        route: RouteName,
        evidence: list[Evidence],
        include_evidence: bool,
        reason: str,
    ) -> QueryResponse:
        """Generate a response from an accepted route and evidence."""


class CompassService:
    """Application service wiring retrieval, routing, and response generation."""

    def __init__(
        self,
        retriever: VectorStore | None = None,
        router: DeterministicRouter | None = None,
        generator: Generator | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or load_settings()
        self.entries = load_corpus()
        self.chunks = chunk_corpus(self.entries)
        self.store = retriever or build_retriever(self.settings)
        if retriever is None:
            self.store.add(self.chunks)
        self.router = router or DeterministicRouter()
        self.generator = generator or build_generator(self.settings) or generate_response

    def query(self, request: QueryRequest) -> QueryResponse:
        """Answer a request using retrieval, routing, and generation."""
        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span("compass.query") as query_span:
            query_span.set_attribute("compass.top_k", request.top_k)
            query_span.set_attribute("compass.include_evidence", request.include_evidence)
            with tracer.start_as_current_span("rag.retrieve") as retrieve_span:
                candidates = self.store.search(request.question, max(request.top_k, 8))
                retrieve_span.set_attribute("rag.candidate_count", len(candidates))
                if candidates:
                    retrieve_span.set_attribute("rag.top_score", candidates[0].score)
            with tracer.start_as_current_span("rag.accept") as accept_span:
                accepted = self._accepted_evidence(request.question, candidates, request.top_k)
                accept_span.set_attribute("rag.accepted_count", len(accepted))
                if accepted:
                    accept_span.set_attribute("rag.accepted_top_score", accepted[0].score)
            with tracer.start_as_current_span("compass.route") as route_span:
                decision = self.router.route(request.question, accepted)
                route_span.set_attribute("compass.route", decision.route.value)
            evidence = accepted if decision.route.value == "curated" else candidates
            with tracer.start_as_current_span("generation.generate") as generate_span:
                response = self.generator(
                    question=request.question,
                    route=decision.route,
                    evidence=evidence,
                    include_evidence=request.include_evidence,
                    reason=decision.reason,
                )
                generate_span.set_attribute("generation.route", response.route.value)
                generate_span.set_attribute("generation.mode", response.generation_mode.value)
                generate_span.set_attribute(
                    "generation.provider_fallback", bool(response.debug.get("livai_fallback"))
                )
                generate_span.set_attribute(
                    "generation.provider_used", bool(response.debug.get("livai_used"))
                )

            return response

    def health(self) -> dict[str, object]:
        """Return service health and loaded corpus statistics."""
        return {"status": "ok", "corpus": corpus_summary(self.entries), "chunks": len(self.chunks)}

    def _accepted_evidence(
        self,
        question: str,
        candidates: list[Evidence],
        top_k: int,
    ) -> list[Evidence]:
        accepted = getattr(self.store, "accepted", None)
        if callable(accepted):
            result = accepted(question, candidates, top_k)
            if isinstance(result, list):
                return result
        return candidates[:top_k]
