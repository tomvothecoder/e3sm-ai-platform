"""FastAPI application for E3SM-ASSIST phase 1."""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Protocol

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from e3sm_assist.generation import generate_response
from e3sm_assist.ingest import chunk_corpus, corpus_summary, load_corpus
from e3sm_assist.interfaces import VectorStore
from e3sm_assist.livai import build_generator
from e3sm_assist.models import Evidence, QueryRequest, QueryResponse, RouteName
from e3sm_assist.retrieval import InMemoryVectorStore, LexicalEmbedder
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
        self.store = retriever or InMemoryVectorStore(LexicalEmbedder())
        if retriever is None:
            self.store.add(self.chunks)
        self.router = router or DeterministicRouter()
        self.generator = generator or build_generator(self.settings) or generate_response

    def query(self, request: QueryRequest) -> QueryResponse:
        """Answer a request using retrieval, routing, and generation."""
        candidates = self.store.search(request.question, max(request.top_k, 8))
        accepted = self._accepted_evidence(request.question, candidates, request.top_k)
        decision = self.router.route(request.question, accepted)
        evidence = accepted if decision.route.value == "curated" else candidates
        return self.generator(
            question=request.question,
            route=decision.route,
            evidence=evidence,
            include_evidence=request.include_evidence,
            reason=decision.reason,
        )

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


app = FastAPI(title="E3SM-ASSIST Backend", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_cors_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


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
