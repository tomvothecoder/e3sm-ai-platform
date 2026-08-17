"""FastAPI application for E3SM-ASSIST phase 1."""

from __future__ import annotations

from functools import lru_cache
from time import perf_counter
from typing import Annotated, Protocol
from uuid import uuid4

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from opentelemetry import trace
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from e3sm_assist.generation import generate_response
from e3sm_assist.ingest import chunk_corpus, corpus_summary, load_corpus
from e3sm_assist.interfaces import VectorStore
from e3sm_assist.livai import build_generator
from e3sm_assist.models import Evidence, QueryRequest, QueryResponse, RouteName
from e3sm_assist.observability import (
    configure_observability,
    instrument_fastapi,
    log_request_complete,
)
from e3sm_assist.retrieval import build_retriever
from e3sm_assist.router import DeterministicRouter
from e3sm_assist.settings import Settings, load_settings


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


class AssistService:
    """Application service wiring retrieval, routing, and generation."""

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
        with tracer.start_as_current_span("assist.query") as query_span:
            query_span.set_attribute("assist.top_k", request.top_k)
            query_span.set_attribute("assist.include_evidence", request.include_evidence)
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
            with tracer.start_as_current_span("assist.route") as route_span:
                decision = self.router.route(request.question, accepted)
                route_span.set_attribute("assist.route", decision.route.value)
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

    def health(self) -> dict[str, object]:
        """Return service health and loaded corpus statistics."""
        return {"status": "ok", "corpus": corpus_summary(self.entries), "chunks": len(self.chunks)}


@lru_cache(maxsize=1)
def get_service() -> AssistService:
    """Return the process-cached application service."""
    return AssistService()


def allowed_cors_origins() -> list[str]:
    """Read safe comma-separated CORS origins for local prototype frontend access."""
    return list(load_settings().cors_allow_origins)


class RequestObservabilityMiddleware(BaseHTTPMiddleware):
    """Attach server-generated request IDs and log bounded request outcomes."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Process an HTTP request without recording headers or bodies."""
        started = perf_counter()
        request_id = uuid4().hex
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            route = request.scope.get("route")
            route_path = getattr(route, "path", "unmatched")
            log_request_complete(
                {
                    "request_id": request_id,
                    "http_method": request.method,
                    "http_route": route_path,
                    "http_status_code": status_code,
                    "duration_ms": round((perf_counter() - started) * 1000, 3),
                    "outcome": "success" if status_code < 500 else "error",
                }
            )


app = FastAPI(title="E3SM-ASSIST Backend", version="0.1.0")
_settings = load_settings()
configure_observability(_settings)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_cors_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "traceparent", "tracestate"],
    expose_headers=["X-Request-ID"],
)
app.add_middleware(RequestObservabilityMiddleware)
instrument_fastapi(app)


@app.get("/health")
def health(service: Annotated[AssistService, Depends(get_service)]) -> dict[str, object]:
    """Return the health endpoint response."""
    return service.health()


@app.post("/query", response_model=QueryResponse)
def query(
    request: QueryRequest,
    service: Annotated[AssistService, Depends(get_service)],
) -> QueryResponse:
    """Return the response for a query endpoint request."""
    return service.query(request)
