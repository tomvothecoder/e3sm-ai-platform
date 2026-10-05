"""Pydantic API contracts and internal data models."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, HttpUrl, field_serializer


class RouteName(StrEnum):
    """Deterministic route labels exposed for evaluation/debugging."""

    CURATED_RAG = "curated"
    WEB_SEARCH = "web"
    OPERATIONAL_TOOL = "future_operational"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class GenerationMode(StrEnum):
    """Resolved response generation method exposed to API consumers."""

    DETERMINISTIC = "deterministic"
    LLM = "llm"
    DETERMINISTIC_FALLBACK = "deterministic_fallback"


ROUTE_ALIASES: dict[RouteName, str] = {
    RouteName.CURATED_RAG: "curated_rag",
    RouteName.WEB_SEARCH: "web_search",
    RouteName.OPERATIONAL_TOOL: "operational_tool",
    RouteName.INSUFFICIENT_EVIDENCE: "insufficient_evidence",
}


class QueryRequest(BaseModel):
    """Request body for POST /query."""

    question: str = Field(min_length=3, max_length=1_000)
    top_k: int = Field(default=4, ge=1, le=10)
    include_evidence: bool = True


class SourceMetadata(BaseModel):
    """Source/provenance metadata retained through ingestion and retrieval."""

    source_id: str
    title: str
    url: HttpUrl
    section: str
    component: str
    version: str
    authority: str = "official"
    provenance: str


class Citation(BaseModel):
    """Citation rendered from retrieved curated evidence."""

    source_id: str
    title: str
    url: HttpUrl
    section: str
    component: str
    version: str
    authority: str
    provenance: str


class Evidence(BaseModel):
    """Retrieved chunk evidence returned for transparent evaluation."""

    chunk_id: str
    text: str
    score: float
    source: SourceMetadata
    matched_terms: list[str] = Field(default_factory=list)
    coverage: float = 0.0
    retrieval_mode: str = "lexical"
    lexical_score: float | None = None
    semantic_score: float | None = None


class RetrievedEvidence(BaseModel):
    """Flat evidence DTO expected by the independent evaluation adapter/client."""

    chunk_id: str
    source_id: str
    title: str
    url: HttpUrl
    section: str
    component: str
    provenance: str
    text: str
    score: float
    matched_terms: list[str] = Field(default_factory=list)
    coverage: float = 0.0
    retrieval_mode: str = "lexical"
    lexical_score: float | None = None
    semantic_score: float | None = None


class QueryResponse(BaseModel):
    """Response body for POST /query."""

    answer: str
    route: RouteName
    route_alias: str
    citations: list[Citation] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    retrieved_evidence: list[RetrievedEvidence] = Field(default_factory=list)
    insufficient_evidence: bool = False
    generation_mode: GenerationMode = GenerationMode.DETERMINISTIC
    debug: dict[str, Any] = Field(default_factory=dict)

    @field_serializer("debug")
    def serialize_debug(self, debug: dict[str, Any]) -> dict[str, Any]:
        """Exclude the user question from the public debug response."""
        return {key: value for key, value in debug.items() if key != "question"}


class CorpusEntry(BaseModel):
    """A curated source section before chunking."""

    source_id: str
    title: str
    url: HttpUrl
    section: str
    component: str
    version: str
    authority: str = "official"
    provenance: str
    text: str


class DocumentChunk(BaseModel):
    """Searchable chunk produced from a curated source section."""

    chunk_id: str
    text: str
    source: SourceMetadata
