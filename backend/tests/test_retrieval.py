from e3sm_assist.ingest import chunk_corpus, load_corpus
from e3sm_assist.retrieval import InMemoryVectorStore, LexicalEmbedder, tokenize


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
