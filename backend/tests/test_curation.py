"""Focused tests for the offline corpus curation workflow."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from e3sm_assist.curation import (
    CurationValidationError,
    capture,
    refresh,
    validate_corpus,
    validate_source_scope,
)


def _manifest(tmp_path, *, source_id: str = "guide", content: str = "# Guide\n"):
    """Create one local-only manifest input for a curation test."""
    (tmp_path / "source.md").write_text(content, encoding="utf-8", newline="\n")
    manifest = {
        "sources": [
            {
                "id": source_id,
                "url": f"https://example.test/{source_id}",
                "revision": "v1.2.3",
                "license": "CC-BY-4.0",
                "policy": "approved",
                "content_path": "source.md",
            }
        ]
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def test_capture_is_deterministic_and_preserves_markdown_structure(tmp_path):
    """Capture normalizes transport details without changing Markdown fences/headings."""
    content = "# Heading  \r\n\r\n```python\r\nprint('x')  \r\n```\r\n"
    normalized = "# Heading\n\n```python\nprint('x')\n```\n"
    manifest = _manifest(tmp_path, content=content)
    first, second = tmp_path / "first", tmp_path / "second"
    capture(manifest, first)
    capture(manifest, second)
    assert (first / "snapshot.json").read_bytes() == (second / "snapshot.json").read_bytes()
    assert (first / "content/guide.md").read_text() == normalized
    record = json.loads((first / "snapshot.json").read_text())["records"][0]
    assert record["sha256"] == hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    assert validate_corpus(first) == []


def test_refresh_never_mutates_baseline_or_needs_network(tmp_path):
    """Refresh uses local files and writes all candidate changes outside baseline."""
    manifest = _manifest(tmp_path)
    baseline, candidate = tmp_path / "baseline", tmp_path / "candidate"
    capture(manifest, baseline)
    baseline_before = (baseline / "snapshot.json").read_bytes()
    (tmp_path / "source.md").write_text("# Changed\n", encoding="utf-8")
    changes = refresh(baseline, manifest, candidate)
    assert [record.id for record in changes.changed] == ["guide"]
    assert (baseline / "snapshot.json").read_bytes() == baseline_before
    assert (candidate / "changes.json").is_file()


def test_capture_wraps_invalid_utf8_as_curation_error(tmp_path):
    """Malformed local capture content fails through the CLI-facing error type."""
    manifest = _manifest(tmp_path)
    (tmp_path / "source.md").write_bytes(b"\xff\xfe")
    with pytest.raises(CurationValidationError, match="invalid UTF-8 content for guide"):
        capture(manifest, tmp_path / "corpus")


def test_validation_detects_tampering_duplicates_and_approval_invalidation(tmp_path):
    """Validation reports hash, duplicate, and missing approval failures offline."""
    manifest = _manifest(tmp_path)
    corpus = tmp_path / "corpus"
    capture(manifest, corpus)
    assert "review is not approved" in validate_corpus(corpus, require_approved=True)
    review = json.loads((corpus / "review.json").read_text())
    review["approved"] = True
    (corpus / "review.json").write_text(json.dumps(review), encoding="utf-8")
    assert validate_corpus(corpus, require_approved=True) == []
    (corpus / "content/guide.md").write_text("tampered\n", encoding="utf-8")
    assert any(
        "content hash mismatch" in failure
        for failure in validate_corpus(corpus, require_approved=True)
    )
    snapshot = json.loads((corpus / "snapshot.json").read_text())
    snapshot["records"].append(snapshot["records"][0])
    (corpus / "snapshot.json").write_text(json.dumps(snapshot), encoding="utf-8")
    failures = validate_corpus(corpus, require_approved=True)
    assert "duplicate IDs" in failures
    assert "duplicate URLs" in failures
    assert "duplicate content hashes" in failures
    with pytest.raises(CurationValidationError):
        capture(
            tmp_path / "missing-manifest.json",
            tmp_path / "unused",
        )


def test_checked_in_acquisition_scope_validates_offline():
    """The repository's acquisition policy is distinct from a capture manifest."""
    scope = Path(__file__).parents[2] / "corpus" / "sources.json"
    assert validate_source_scope(scope) == []


def test_acquisition_scope_rejects_invalid_policy_and_documents(tmp_path):
    """Scope validation rejects unsafe policy values and unpinned selected documents."""
    source = json.loads((Path(__file__).parents[2] / "corpus" / "sources.json").read_text())
    bad = deepcopy(source)
    first = bad["sources"][0]
    first["identity"] = " "
    first["canonical_url"] = "file:///local"
    first["request_interval_seconds"] = 0
    first["path_scope"]["include"] = ["../private"]
    first["documents"] = [
        {
            "id": "unsafe/id",
            "path": "docs/[broken",
            "url": "not-a-url",
            "revision": "main",
            "provenance": "",
        }
    ]
    bad["sources"].append(deepcopy(first))
    path = tmp_path / "bad-sources.json"
    path.write_text(json.dumps(bad), encoding="utf-8")
    failures = validate_source_scope(path)
    assert any("duplicate source IDs" in failure for failure in failures)
    assert any("missing identity" in failure for failure in failures)
    assert any("invalid canonical_url" in failure for failure in failures)
    assert any("request_interval_seconds" in failure for failure in failures)
    assert any("invalid path pattern" in failure for failure in failures)
    assert any("unpinned document revision" in failure for failure in failures)
    assert any("missing document provenance" in failure for failure in failures)
