from pydantic import HttpUrl, TypeAdapter

from e3sm_assist.ingest import chunk_corpus, chunk_entry, load_corpus
from e3sm_assist.models import CorpusEntry

_HTTP_URL_ADAPTER: TypeAdapter[HttpUrl] = TypeAdapter(HttpUrl)


def test_load_curated_corpus_has_representative_official_entries() -> None:
    entries = load_corpus()

    assert 20 <= len(entries) <= 50
    expected = {"User Guide", "Running E3SM", "EAM", "EAMxx", "ELM", "Diagnostics"}
    assert expected.issubset({entry.component for entry in entries})
    assert "E3SM-Unified" in {entry.component for entry in entries}
    assert all(entry.authority == "official" for entry in entries)
    assert all(str(entry.url).startswith("https://docs.e3sm.org/") for entry in entries)


def test_curated_corpus_excludes_retired_documentation_routes() -> None:
    retired_paths = (
        "/E3SM/user-guide/cases/",
        "/E3SM/user-guide/compsets/",
        "/E3SM/user-guide/grids/",
        "/E3SM/user-guide/running-e3sm/",
        "/E3SM/EAM/tech-guide/physics/",
        "/E3SM/EAM/tech-guide/history/",
        "/E3SM/EAMxx/user/input-files/",
        "/E3SM/EAMxx/user/diagnostics/",
        "/E3SM/ELM/user-guide/surface-data/",
        "/E3SM/ELM/user-guide/parameters/",
        "/E3SM/ELM/user-guide/history-fields/",
        "/e3sm_diags/_build/html/main/parameters.html",
        "/e3sm_diags/_build/html/main/run.html",
        "/e3sm_diags/_build/html/main/viewer.html",
        "/e3sm-unified/main/installation.html",
    )

    assert not any(path in str(entry.url) for entry in load_corpus() for path in retired_paths)


def test_running_guide_citations_use_current_topic_specific_pages() -> None:
    entries_by_id = {entry.source_id: str(entry.url) for entry in load_corpus()}
    prior_to_production = "https://docs.e3sm.org/running-e3sm-guide/guide-prior-to-production/"
    production = "https://docs.e3sm.org/running-e3sm-guide/guide-production/"
    post_processing = "https://docs.e3sm.org/running-e3sm-guide/guide-post-processing/"

    assert entries_by_id["running-guide:create-newcase"] == prior_to_production
    assert entries_by_id["running-guide:case-setup"] == prior_to_production
    assert entries_by_id["running-case-build"] == prior_to_production
    assert entries_by_id["running-guide:run-and-submit"] == production
    assert entries_by_id["running-xmlchange"] == production
    assert entries_by_id["user-guide:namelists"] == prior_to_production
    assert entries_by_id["running-restarts"] == production
    assert entries_by_id["user-guide:history-output"] == post_processing


def test_chunk_entry_is_deterministic_and_preserves_source_metadata() -> None:
    entry = CorpusEntry(
        source_id="sample",
        title="Sample",
        url=_HTTP_URL_ADAPTER.validate_python("https://docs.e3sm.org/E3SM/user-guide/sample/"),
        section="Sample Section",
        component="User Guide",
        version="latest",
        authority="official",
        provenance="test fixture",
        text=(
            "First sentence has relevant details. Second sentence has additional details. "
            "Third sentence ends the entry."
        ),
    )

    chunks = chunk_entry(entry, max_words=8, overlap_words=2)

    assert [chunk.chunk_id for chunk in chunks] == [
        "sample#chunk-1",
        "sample#chunk-2",
        "sample#chunk-3",
    ]
    assert chunks[0].source.source_id == "sample"
    assert chunks[0].source.section == "Sample Section"
    assert "details. Second" in chunks[1].text


def test_chunk_corpus_uses_all_entries() -> None:
    entries = load_corpus()
    chunks = chunk_corpus(entries, max_words=60, overlap_words=10)

    source_ids = {chunk.source.source_id for chunk in chunks}
    assert source_ids == {entry.source_id for entry in entries}
    assert len(chunks) >= len(entries)
