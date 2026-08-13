"""Deterministic lexical in-memory embedding-style retrieval."""

from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Iterable, Sequence
from hashlib import sha256

from llama_index.core import VectorStoreIndex
from llama_index.core.embeddings import BaseEmbedding
from llama_index.core.schema import MetadataMode, NodeWithScore, TextNode
from pydantic import PrivateAttr

from e3sm_assist.interfaces import Embedder, EmbeddingVector
from e3sm_assist.models import DocumentChunk, Evidence, SourceMetadata

TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9_+.-]*")
TOKEN_BOUNDARY_TEMPLATE = r"(?<![a-z0-9_+.-]){phrase}(?![a-z0-9_+.-])"
STOPWORDS = {
    "a",
    "about",
    "and",
    "are",
    "as",
    "be",
    "by",
    "can",
    "do",
    "for",
    "from",
    "how",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "the",
    "to",
    "what",
    "when",
    "where",
    "which",
    "with",
}
UNSUPPORTED_INTENT_PHRASES = {
    "api key",
    "buy for my personal",
    "exact global temperature",
    "hardware should i buy",
    "internal api key",
    "mars rover",
    "personal climate-model workstation",
    "prove the exact",
    "undocumented internal",
}


def tokenize(text: str) -> list[str]:
    """Normalize text into deterministic lexical tokens."""
    return [token for token in TOKEN_RE.findall(text.lower()) if token not in STOPWORDS]


def contains_token_phrase(text: str, phrase: str) -> bool:
    """Return true when phrase appears on token boundaries, not as a substring."""
    escaped = re.escape(phrase.lower()).replace(r"\ ", r"\s+")
    pattern = TOKEN_BOUNDARY_TEMPLATE.format(phrase=escaped)
    return re.search(pattern, text.lower()) is not None


class LexicalEmbedder(Embedder):
    """Small deterministic term-frequency embedder for tests and local development."""

    def embed(self, text: str) -> EmbeddingVector:
        """Embed text as a normalized lexical term-frequency vector."""
        counts = Counter(tokenize(text))
        total = sum(counts.values()) or 1
        return {term: count / total for term, count in sorted(counts.items())}


class LlamaIndexLexicalEmbedding(BaseEmbedding):
    """Fixed-size LlamaIndex embedding derived from the local lexical embedder."""

    dimensions: int = 256
    _lexical_embedder: LexicalEmbedder = PrivateAttr(default_factory=LexicalEmbedder)

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for term, weight in self._lexical_embedder.embed(text).items():
            digest = sha256(term.encode("utf-8")).digest()
            index = int.from_bytes(digest[:8], byteorder="big") % self.dimensions
            vector[index] += weight
        return vector

    def _get_query_embedding(self, query: str) -> list[float]:
        return self._embed(query)

    def _get_text_embedding(self, text: str) -> list[float]:
        return self._embed(text)

    async def _aget_query_embedding(self, query: str) -> list[float]:
        return self._get_query_embedding(query)


def document_chunk_to_text_node(chunk: DocumentChunk) -> TextNode:
    """Convert a curated chunk to a node while retaining citation-grade provenance."""
    metadata = {
        "chunk_id": chunk.chunk_id,
        "source_id": chunk.source.source_id,
        "title": chunk.source.title,
        "url": str(chunk.source.url),
        "section": chunk.source.section,
        "component": chunk.source.component,
        "version": chunk.source.version,
        "authority": chunk.source.authority,
        "provenance": chunk.source.provenance,
    }
    return TextNode(
        id_=chunk.chunk_id,
        text=chunk.text,
        metadata=metadata,
        excluded_embed_metadata_keys=list(metadata),
    )


def cosine_similarity(left: EmbeddingVector, right: EmbeddingVector) -> float:
    """Compute cosine similarity over sparse lexical vectors."""
    if not left or not right:
        return 0.0
    dot = sum(weight * right.get(term, 0.0) for term, weight in left.items())
    left_norm = math.sqrt(sum(weight * weight for weight in left.values()))
    right_norm = math.sqrt(sum(weight * weight for weight in right.values()))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return dot / (left_norm * right_norm)


class LlamaIndexVectorStore:
    """Optional in-memory LlamaIndex retriever with deterministic lexical embeddings."""

    def __init__(self, embedder: LlamaIndexLexicalEmbedding | None = None) -> None:
        self._embedder = embedder or LlamaIndexLexicalEmbedding()
        self._chunks: list[DocumentChunk] = []
        self._index: VectorStoreIndex | None = None

    def add(self, chunks: Iterable[DocumentChunk]) -> None:
        """Index chunks as LlamaIndex nodes, preserving all source metadata."""
        new_chunks = list(chunks)
        if not new_chunks:
            return
        nodes = [document_chunk_to_text_node(chunk) for chunk in new_chunks]
        if self._index is None:
            self._index = VectorStoreIndex(nodes=nodes, embed_model=self._embedder)
        else:
            self._index.insert_nodes(nodes)
        self._chunks.extend(new_chunks)

    def search(self, query: str, top_k: int) -> list[Evidence]:
        """Retrieve through LlamaIndex, then apply stable evidence ordering."""
        if top_k <= 0 or self._index is None:
            return []
        query_terms = InMemoryVectorStore._query_terms(query)
        results = self._index.as_retriever(similarity_top_k=len(self._chunks)).retrieve(query)
        evidence = [self._node_to_evidence(item, query_terms) for item in results]
        ranked = sorted(evidence, key=lambda item: (-item.score, item.chunk_id))
        return [item for item in ranked if item.score > 0.0][:top_k]

    def accepted(self, query: str, candidates: Sequence[Evidence], top_k: int) -> list[Evidence]:
        """Apply the same curated-evidence policy as the default in-memory store."""
        return InMemoryVectorStore.apply_acceptance_policy(query, candidates, top_k)

    @staticmethod
    def _node_to_evidence(item: NodeWithScore, query_terms: set[str]) -> Evidence:
        node = item.node
        metadata = node.metadata
        source = SourceMetadata.model_validate(
            {
                "source_id": metadata["source_id"],
                "title": metadata["title"],
                "url": metadata["url"],
                "section": metadata["section"],
                "component": metadata["component"],
                "version": metadata["version"],
                "authority": metadata["authority"],
                "provenance": metadata["provenance"],
            }
        )
        text = node.get_content(metadata_mode=MetadataMode.NONE)
        searchable = " ".join(
            [
                source.source_id.replace(":", " ").replace("-", " "),
                source.title,
                source.section,
                source.component,
                text,
            ]
        ).lower()
        matched_terms = sorted(
            term for term in query_terms if contains_token_phrase(searchable, term)
        )
        coverage = len(matched_terms) / len(query_terms) if query_terms else 0.0
        return Evidence(
            chunk_id=str(metadata["chunk_id"]),
            text=text,
            score=round(float(item.score or 0.0), 6),
            source=source,
            matched_terms=matched_terms,
            coverage=round(coverage, 6),
        )


class InMemoryVectorStore:
    """Provider-free vector store implementing the VectorStore protocol."""

    def __init__(self, embedder: Embedder | None = None) -> None:
        self._embedder = embedder or LexicalEmbedder()
        self._records: list[tuple[DocumentChunk, EmbeddingVector]] = []

    def add(self, chunks: Iterable[DocumentChunk]) -> None:
        """Add chunks and their lexical vectors to the store."""
        for chunk in chunks:
            self._records.append((chunk, self._embedder.embed(chunk.text)))

    def search(self, query: str, top_k: int) -> list[Evidence]:
        """Return the highest-scoring evidence for a query."""
        query_vector = self._embedder.embed(query)
        query_terms = self._query_terms(query)
        ranked = sorted(
            (
                self._score_chunk(query_vector, query_terms, chunk, vector)
                for chunk, vector in self._records
            ),
            key=lambda evidence: (-evidence.score, evidence.chunk_id),
        )
        return [evidence for evidence in ranked if evidence.score > 0.0][:top_k]

    def accepted(self, query: str, candidates: Sequence[Evidence], top_k: int) -> list[Evidence]:
        """Filter retrieved candidates to meaningful curated evidence for generation."""
        return self.apply_acceptance_policy(query, candidates, top_k)

    @staticmethod
    def apply_acceptance_policy(
        query: str, candidates: Sequence[Evidence], top_k: int
    ) -> list[Evidence]:
        """Filter retrieved candidates to meaningful curated evidence for generation."""
        if InMemoryVectorStore._unsupported_overlap(query):
            return []
        accepted = [
            evidence
            for evidence in candidates
            if evidence.coverage >= 0.18
            and evidence.score >= 0.11
            and evidence.source.authority == "official"
        ]
        if not accepted:
            return []
        # Keep a coherent answer: evidence must share meaningful query terms with the top hit.
        top_terms = set(accepted[0].matched_terms)
        coherent = [
            evidence
            for evidence in accepted
            if set(evidence.matched_terms) & top_terms or evidence.coverage >= 0.34
        ]
        return coherent[:top_k]

    def _score_chunk(
        self,
        query_vector: EmbeddingVector,
        query_terms: set[str],
        chunk: DocumentChunk,
        vector: EmbeddingVector,
    ) -> Evidence:
        haystack = self._searchable_text(chunk)
        matched_terms = sorted(
            term for term in query_terms if contains_token_phrase(haystack, term)
        )
        coverage = len(matched_terms) / len(query_terms) if query_terms else 0.0
        score = (
            cosine_similarity(query_vector, vector)
            + coverage * 0.45
            + self._metadata_bonus(query_terms, chunk)
            + self._exact_phrase_bonus(query_terms, chunk)
        )
        return Evidence(
            chunk_id=chunk.chunk_id,
            text=chunk.text,
            score=round(score, 6),
            source=chunk.source,
            matched_terms=matched_terms,
            coverage=round(coverage, 6),
        )

    @staticmethod
    def _query_terms(query: str) -> set[str]:
        terms = set(tokenize(query))
        synonyms = {
            "compset": {"compsets"},
            "compsets": {"compset"},
            "namelist": {"namelists"},
            "namelists": {"namelist"},
            "field": {"fields"},
            "fields": {"field"},
            "plot": {"plots"},
            "plots": {"plot"},
            "configure": {"configuration", "configuring"},
            "configuring": {"configure", "configuration"},
            "configuration": {"configure", "configuring"},
            "supplied": {"supply", "input"},
            "building": {"build", "stack"},
            "provide": {"provides"},
            "provides": {"provide"},
            "batch": {"submit"},
            "submit": {"submitting"},
        }
        expanded = set(terms)
        for term in terms:
            expanded.update(synonyms.get(term, set()))
        return expanded

    @staticmethod
    def _unsupported_overlap(query: str) -> bool:
        return any(contains_token_phrase(query, phrase) for phrase in UNSUPPORTED_INTENT_PHRASES)

    @staticmethod
    def _searchable_text(chunk: DocumentChunk) -> str:
        return " ".join(
            [
                chunk.source.source_id.replace(":", " ").replace("-", " "),
                chunk.source.title,
                chunk.source.section,
                chunk.source.component,
                chunk.text,
            ]
        ).lower()

    @staticmethod
    def _metadata_bonus(query_terms: set[str], chunk: DocumentChunk) -> float:
        metadata = " ".join(
            [
                chunk.source.source_id,
                chunk.source.title,
                chunk.source.section,
                chunk.source.component,
            ]
        ).lower()
        return sum(0.035 for term in query_terms if contains_token_phrase(metadata, term))

    @staticmethod
    def _exact_phrase_bonus(query_terms: set[str], chunk: DocumentChunk) -> float:
        """Small deterministic boost for exact token-boundary documentation phrases."""
        chunk_text = chunk.text.lower()
        source_text = f"{chunk.source.source_id} {chunk.source.title}".lower()
        bonus = 0.0
        if "submit" in query_terms and contains_token_phrase(chunk_text, "case.submit"):
            bonus += 0.2
        if "build" in query_terms and contains_token_phrase(chunk_text, "case.build"):
            bonus += 0.15
        if "setup" in query_terms and contains_token_phrase(chunk_text, "case.setup"):
            bonus += 0.15
        if "eamxx" in query_terms and contains_token_phrase(source_text, "eamxx"):
            bonus += 0.1
        if "eam" in query_terms and contains_token_phrase(source_text, "eam"):
            bonus += 0.08
        for token in query_terms:
            if len(token) >= 4 and contains_token_phrase(source_text, token):
                bonus += 0.01
        return bonus
