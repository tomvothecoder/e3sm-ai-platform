"""Provider-independent extension points for retrieval and external sources."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Protocol

from e3sm_assist.models import DocumentChunk, Evidence

EmbeddingVector = dict[str, float]


class Embedder(Protocol):
    """Embedding abstraction; deterministic lexical implementation ships in phase 1."""

    def embed(self, text: str) -> EmbeddingVector:
        """Return a vector representation for text."""


class VectorStore(Protocol):
    """Vector retrieval interface compatible with pgvector or other stores later."""

    def add(self, chunks: Iterable[DocumentChunk]) -> None:
        """Index chunks."""

    def search(self, query: str, top_k: int) -> list[Evidence]:
        """Return ranked evidence for query."""


class Reranker(Protocol):
    """Optional reranking extension point for cross-encoders or LLM rerankers."""

    def rerank(self, query: str, candidates: Sequence[Evidence], top_k: int) -> list[Evidence]:
        """Return reranked evidence."""


class HybridRetriever(Protocol):
    """Optional extension point for lexical/vector/hybrid retrieval."""

    def retrieve(self, query: str, top_k: int) -> list[Evidence]:
        """Return retrieved evidence."""


class WebSource(Protocol):
    """Future web-search provider boundary; phase 1 does not call the network."""

    def search(self, query: str, top_k: int) -> list[Evidence]:
        """Return web evidence from an external provider."""


class OperationalToolSource(Protocol):
    """Future SimBoard/GitHub/API/MCP/tool-calling provider boundary."""

    def run(self, query: str) -> list[Evidence]:
        """Return operational/tool evidence."""
