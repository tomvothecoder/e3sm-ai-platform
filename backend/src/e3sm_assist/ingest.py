"""Curated corpus loading and deterministic chunking."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from e3sm_assist.models import CorpusEntry, DocumentChunk, SourceMetadata

DEFAULT_CORPUS_PATH = Path(__file__).parent / "data" / "curated_corpus.json"
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


def load_corpus(path: Path = DEFAULT_CORPUS_PATH) -> list[CorpusEntry]:
    """Load curated source entries from bundled static JSON."""

    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("curated corpus must be a JSON list")
    return [CorpusEntry.model_validate(item) for item in raw]


def chunk_entry(
    entry: CorpusEntry,
    max_words: int = 90,
    overlap_words: int = 15,
) -> list[DocumentChunk]:
    """Split one curated entry into stable word-bounded chunks.

    The algorithm prefers sentence boundaries, applies a small word overlap only when an
    entry spans multiple chunks, and keeps chunk IDs deterministic for citation tests.
    """

    if max_words <= 0:
        raise ValueError("max_words must be positive")
    if overlap_words < 0 or overlap_words >= max_words:
        raise ValueError("overlap_words must be non-negative and smaller than max_words")

    sentences = [
        sentence.strip() for sentence in SENTENCE_RE.split(entry.text.strip()) if sentence.strip()
    ]
    chunks: list[list[str]] = []
    current: list[str] = []

    for sentence in sentences:
        words = sentence.split()
        if current and len(current) + len(words) > max_words:
            chunks.append(current)
            current = current[-overlap_words:] if overlap_words else []
        current.extend(words)

    if current:
        chunks.append(current)

    source = SourceMetadata(**entry.model_dump(exclude={"text"}))
    return [
        DocumentChunk(
            chunk_id=f"{entry.source_id}#chunk-{index + 1}",
            text=" ".join(words),
            source=source,
        )
        for index, words in enumerate(chunks)
    ]


def chunk_corpus(
    entries: list[CorpusEntry],
    max_words: int = 90,
    overlap_words: int = 15,
) -> list[DocumentChunk]:
    """Chunk all curated entries preserving corpus order."""

    return [
        chunk
        for entry in entries
        for chunk in chunk_entry(entry, max_words=max_words, overlap_words=overlap_words)
    ]


def corpus_summary(entries: list[CorpusEntry]) -> dict[str, Any]:
    """Return lightweight corpus statistics for health/debug endpoints."""

    components = sorted({entry.component for entry in entries})
    return {"entries": len(entries), "components": components}
