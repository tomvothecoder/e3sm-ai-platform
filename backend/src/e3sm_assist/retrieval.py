"""Deterministic lexical in-memory embedding-style retrieval."""

from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Iterable, Sequence

from e3sm_assist.interfaces import Embedder, EmbeddingVector
from e3sm_assist.models import DocumentChunk, Evidence

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
        counts = Counter(tokenize(text))
        total = sum(counts.values()) or 1
        return {term: count / total for term, count in sorted(counts.items())}


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


class InMemoryVectorStore:
    """Provider-free vector store implementing the VectorStore protocol."""

    def __init__(self, embedder: Embedder | None = None) -> None:
        self._embedder = embedder or LexicalEmbedder()
        self._records: list[tuple[DocumentChunk, EmbeddingVector]] = []

    def add(self, chunks: Iterable[DocumentChunk]) -> None:
        for chunk in chunks:
            self._records.append((chunk, self._embedder.embed(chunk.text)))

    def search(self, query: str, top_k: int) -> list[Evidence]:
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

        if self._unsupported_overlap(query):
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
