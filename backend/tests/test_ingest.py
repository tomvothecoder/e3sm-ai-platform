from e3sm_assist.ingest import chunk_corpus, chunk_entry, load_corpus
from e3sm_assist.models import CorpusEntry
from pydantic import HttpUrl, TypeAdapter

_HTTP_URL_ADAPTER: TypeAdapter[HttpUrl] = TypeAdapter(HttpUrl)


def test_load_curated_corpus_has_representative_official_entries() -> None:
    entries = load_corpus()

    assert 20 <= len(entries) <= 50
    expected = {"User Guide", "Running E3SM", "EAM", "EAMxx", "ELM", "Diagnostics"}
    assert expected.issubset({entry.component for entry in entries})
    assert "E3SM-Unified" in {entry.component for entry in entries}
    assert all(entry.authority == "official" for entry in entries)
    official_prefixes = ("https://docs.e3sm.org/", "https://e3sm-project.github.io/")
    assert all(str(entry.url).startswith(official_prefixes) for entry in entries)


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
