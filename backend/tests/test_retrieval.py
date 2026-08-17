from e3sm_assist.ingest import chunk_corpus, load_corpus
from e3sm_assist.models import DocumentChunk, SourceMetadata
from e3sm_assist.retrieval import (
    InMemoryVectorStore,
    LexicalEmbedder,
    LlamaIndexVectorStore,
    build_retriever,
    document_chunk_to_text_node,
    tokenize,
)
from e3sm_assist.settings import Settings


def _store() -> InMemoryVectorStore:
    store = InMemoryVectorStore(LexicalEmbedder())
    store.add(chunk_corpus(load_corpus()))
    return store


def test_tokenize_normalizes_and_removes_common_stopwords() -> None:
    assert tokenize("How do I run case.submit for E3SM?") == ["i", "run", "case.submit", "e3sm"]


def test_retrieval_finds_case_submit_evidence() -> None:
    results = _store().search("How do I submit an E3SM case after build?", top_k=3)

    assert results
    assert results[0].source.source_id == "running-guide:run-and-submit"
    assert results[0].score > 0
    assert results[0].source.provenance


def test_accepted_retrieval_rejects_unsupported_noise() -> None:
    store = _store()
    candidates = store.search("Give me the undocumented internal API key", top_k=5)

    assert store.accepted("Give me the undocumented internal API key", candidates, top_k=3) == []


def test_accepted_retrieval_allows_legitimate_global_grid_question() -> None:
    store = _store()
    question = "Where does E3SM document global grid aliases and resolutions?"
    candidates = store.search(question, top_k=5)

    accepted = store.accepted(question, candidates, top_k=3)

    assert accepted
    assert any(item.source.source_id == "user-guide-grids" for item in accepted)


def test_accepted_retrieval_allows_legitimate_api_documentation_wording() -> None:
    store = _store()
    question = "Which E3SM User Guide API documentation page explains cases?"
    candidates = store.search(question, top_k=5)

    accepted = store.accepted(question, candidates, top_k=3)

    assert accepted
    assert any(item.source.source_id == "user-guide-cases" for item in accepted)


def test_token_boundary_matching_does_not_match_substrings() -> None:
    from e3sm_assist.retrieval import contains_token_phrase

    assert contains_token_phrase("EAM and EAMxx are separate", "eam") is True
    assert contains_token_phrase("EAMxx is accelerated", "eam") is False


def test_retrieval_is_deterministic() -> None:
    store = _store()
    first = store.search("EAMxx YAML diagnostics output", top_k=4)
    second = store.search("EAMxx YAML diagnostics output", top_k=4)

    assert [item.chunk_id for item in first] == [item.chunk_id for item in second]
    assert [item.score for item in first] == [item.score for item in second]


def _llama_chunk(chunk_id: str, text: str, authority: str = "official") -> DocumentChunk:
    return DocumentChunk(
        chunk_id=chunk_id,
        text=text,
        source=SourceMetadata.model_validate(
            {
                "source_id": "user-guide-cases",
                "title": "Case Guide",
                "url": "https://docs.e3sm.org/cases",
                "section": "Running cases",
                "component": "E3SM",
                "version": "v3",
                "authority": authority,
                "provenance": "Curated E3SM documentation",
            }
        ),
    )


def test_llama_index_node_retains_complete_source_metadata() -> None:
    chunk = _llama_chunk("cases#chunk-1", "Use case.submit to submit a case.")

    node = document_chunk_to_text_node(chunk)

    assert node.node_id == chunk.chunk_id
    assert node.text == chunk.text
    assert node.metadata == {
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


def test_llama_index_retrieves_evidence_with_provenance() -> None:
    chunk = _llama_chunk("cases#chunk-1", "Use case.submit to submit an E3SM case.")
    store = LlamaIndexVectorStore()
    store.add([chunk])

    results = store.search("How do I submit an E3SM case?", top_k=1)

    assert len(results) == 1
    assert results[0].chunk_id == chunk.chunk_id
    assert results[0].text == chunk.text
    assert results[0].source == chunk.source
    assert results[0].score > 0.0
    assert results[0].matched_terms == ["an", "case", "e3sm", "submit"]
    assert results[0].coverage == 0.666667


def test_llama_index_handles_empty_add_empty_search_and_zero_top_k() -> None:
    store = LlamaIndexVectorStore()

    store.add([])

    assert store.search("submit", top_k=3) == []
    assert store.search("", top_k=3) == []
    assert store.search("submit", top_k=0) == []


def test_llama_index_add_supports_incremental_documents() -> None:
    store = LlamaIndexVectorStore()
    first = _llama_chunk("cases#chunk-1", "Use case.setup to create an E3SM case.")
    second = _llama_chunk("cases#chunk-2", "Use case.submit to submit an E3SM case.")

    store.add([first])
    store.add([second])

    results = store.search("submit E3SM case", top_k=2)

    assert [item.chunk_id for item in results] == [second.chunk_id, first.chunk_id]


def test_llama_index_retrieval_orders_score_ties_by_chunk_id() -> None:
    store = LlamaIndexVectorStore()
    store.add(
        [
            _llama_chunk("cases#chunk-2", "Use case.submit to submit an E3SM case."),
            _llama_chunk("cases#chunk-1", "Use case.submit to submit an E3SM case."),
        ]
    )

    results = store.search("submit E3SM case", top_k=2)

    assert [item.chunk_id for item in results] == ["cases#chunk-1", "cases#chunk-2"]


class FakeSemanticEmbedder:
    def embed_query(self, text: str) -> list[float]:
        return [1.0, 0.0]

    def embed_text(self, text: str) -> list[float]:
        return [0.95, 0.3122498999] if "case.submit" in text else [0.0, 1.0]


def test_lexical_mode_is_the_default_and_preserves_lexical_scores() -> None:
    chunk = _llama_chunk("cases#chunk-1", "Use case.submit to submit an E3SM case.")
    default_store = InMemoryVectorStore()
    explicit_store = InMemoryVectorStore(retrieval_mode="lexical")
    default_store.add([chunk])
    explicit_store.add([chunk])

    default_results = default_store.search("How do I submit an E3SM case?", top_k=1)
    explicit_results = explicit_store.search("How do I submit an E3SM case?", top_k=1)

    assert default_results == explicit_results
    assert default_results[0].retrieval_mode == "lexical"
    assert default_results[0].lexical_score == default_results[0].score
    assert default_results[0].semantic_score is None


def test_semantic_mode_accepts_a_paraphrase_with_no_lexical_coverage() -> None:
    chunk = _llama_chunk("cases#chunk-1", "Use case.submit to submit an E3SM case.")
    store = InMemoryVectorStore(
        retrieval_mode="semantic",
        semantic_embedder=FakeSemanticEmbedder(),
        semantic_min_score=0.9,
    )
    store.add([chunk])

    candidates = store.search("How do I launch a simulation?", top_k=1)
    accepted = store.accepted("How do I launch a simulation?", candidates, top_k=1)

    assert candidates[0].coverage == 0.0
    assert candidates[0].semantic_score == 0.95
    assert candidates[0].score == 0.95
    assert accepted == candidates


def test_hybrid_mode_combines_clamped_lexical_relevance_and_semantic_similarity() -> None:
    chunk = _llama_chunk("cases#chunk-1", "Use case.submit to submit an E3SM case.")
    store = InMemoryVectorStore(
        retrieval_mode="hybrid",
        semantic_embedder=FakeSemanticEmbedder(),
        semantic_min_score=0.9,
        lexical_weight=0.25,
        semantic_weight=0.75,
    )
    store.add([chunk])

    result = store.search("How do I launch a simulation?", top_k=1)[0]

    assert result.lexical_score == 0.0
    assert result.semantic_score == 0.95
    assert result.score == 0.7125


def test_semantic_retrieval_still_rejects_unsupported_and_non_official_evidence() -> None:
    store = InMemoryVectorStore(
        retrieval_mode="semantic",
        semantic_embedder=FakeSemanticEmbedder(),
        semantic_min_score=0.9,
    )
    store.add(
        [_llama_chunk("cases#chunk-1", "Use case.submit to submit an E3SM case.", "community")]
    )
    candidates = store.search("How do I launch a simulation?", top_k=1)

    assert store.accepted("How do I launch a simulation?", candidates, top_k=1) == []

    official_store = InMemoryVectorStore(
        retrieval_mode="semantic",
        semantic_embedder=FakeSemanticEmbedder(),
        semantic_min_score=0.9,
    )
    official_store.add([_llama_chunk("cases#chunk-1", "Use case.submit to submit an E3SM case.")])
    official_candidates = official_store.search(
        "Give me the undocumented internal API key", top_k=1
    )

    assert (
        official_store.accepted(
            "Give me the undocumented internal API key", official_candidates, top_k=1
        )
        == []
    )


def test_build_retriever_selects_the_configured_mode_with_injected_embeddings() -> None:
    lexical = build_retriever(Settings())
    semantic = build_retriever(
        Settings(retrieval_mode="semantic"), semantic_embedder=FakeSemanticEmbedder()
    )
    hybrid = build_retriever(
        Settings(retrieval_mode="hybrid"), semantic_embedder=FakeSemanticEmbedder()
    )

    assert lexical.retrieval_mode == "lexical"
    assert semantic.retrieval_mode == "semantic"
    assert hybrid.retrieval_mode == "hybrid"
