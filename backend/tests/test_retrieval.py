from e3sm_assist.ingest import chunk_corpus, load_corpus
from e3sm_assist.models import DocumentChunk, SourceMetadata
from e3sm_assist.retrieval import (
    InMemoryVectorStore,
    LexicalEmbedder,
    LlamaIndexVectorStore,
    document_chunk_to_text_node,
    tokenize,
)


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


def _llama_chunk(chunk_id: str, text: str) -> DocumentChunk:
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
                "authority": "official",
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
