"""Offline, deterministic corpus curation artifacts.

This module deliberately supports two distinct JSON manifests.  An acquisition
*source scope* records approved upstream identity, access, and path policy; it
does not contain captured content and may have no selected documents.  A local
*capture manifest* contains separately approved, pinned local Markdown inputs
(``id``, ``url``, ``revision``, ``license``, ``policy``, ``content_path``).
Capture writes normalized Markdown to ``content/<id>.md`` plus ``snapshot``,
``catalog``, and hash-bound ``review`` artifacts.  Neither validation nor
capture needs network access.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, ValidationError

SCHEMA_VERSION = 1
_SAFE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*\Z")
_FLOATING_REVISIONS = {"head", "main", "master", "latest", "default", "stable"}


class CurationValidationError(ValueError):
    """Raised when a manifest or a corpus artifact fails curation validation."""


class PathScope(BaseModel):
    """Allowed and excluded repository-relative glob patterns for acquisition."""

    model_config = ConfigDict(extra="forbid")

    include: list[str]
    exclude: list[str]


class ScopeDocument(BaseModel):
    """A selected scope document with pinned revision and acquisition provenance."""

    model_config = ConfigDict(extra="forbid")

    id: str
    path: str
    url: str
    revision: str
    provenance: str


class AcquisitionSource(BaseModel):
    """Approved upstream acquisition policy, not a local capture input."""

    model_config = ConfigDict(extra="forbid")

    id: str
    identity: str
    owner: str
    canonical_url: str
    repository_url: str
    license_url: str
    access: str
    redistribution: str
    refresh_cadence: str
    request_interval_seconds: float
    path_scope: PathScope
    document_status: str
    documents: list[ScopeDocument]


class SourceScope(BaseModel):
    """Versioned approved acquisition scope, intentionally separate from capture."""

    model_config = ConfigDict(extra="forbid")

    manifest_version: int
    status: str
    sources: list[AcquisitionSource]


class ApprovedSource(BaseModel):
    """A reviewed source and its manifest-relative local Markdown input."""

    model_config = ConfigDict(extra="forbid")

    id: str
    url: str
    revision: str
    license: str
    policy: str
    content_path: str
    title: str | None = None


class SourceManifest(BaseModel):
    """The versioned list of source inputs accepted for a capture."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = SCHEMA_VERSION
    sources: list[ApprovedSource] = Field(default_factory=list)


class CorpusRecord(BaseModel):
    """A content-addressed captured source in a snapshot and catalog."""

    model_config = ConfigDict(extra="forbid")

    id: str
    url: str
    revision: str
    license: str
    policy: str
    content_path: str
    sha256: str
    title: str | None = None


class Snapshot(BaseModel):
    """A deterministic inventory of captured local documents."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = SCHEMA_VERSION
    records: list[CorpusRecord] = Field(default_factory=list)


class Catalog(BaseModel):
    """The publishable source catalog; it mirrors the snapshot inventory."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = SCHEMA_VERSION
    records: list[CorpusRecord] = Field(default_factory=list)


class ReviewArtifact(BaseModel):
    """Hash-bound review decision for one snapshot and catalog pair."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = SCHEMA_VERSION
    approved: bool = False
    snapshot_sha256: str
    catalog_sha256: str
    record_hashes: dict[str, str]


class ChangeSet(BaseModel):
    """Deterministic difference between baseline and candidate records."""

    model_config = ConfigDict(extra="forbid")

    added: list[CorpusRecord] = Field(default_factory=list)
    changed: list[CorpusRecord] = Field(default_factory=list)
    removed: list[CorpusRecord] = Field(default_factory=list)
    unchanged: list[CorpusRecord] = Field(default_factory=list)


def normalize_markdown(content: str | bytes) -> str:
    """Decode UTF-8 and normalize only line endings, trailing space, and EOF."""
    if isinstance(content, bytes):
        content = content.decode("utf-8")
    content = content.replace("\r\n", "\n").replace("\r", "\n")
    return "\n".join(line.rstrip(" \t") for line in content.split("\n")).rstrip("\n") + "\n"


def content_sha256(content: str | bytes) -> str:
    """Return the SHA-256 digest of normalized UTF-8 Markdown content."""
    return hashlib.sha256(normalize_markdown(content).encode("utf-8")).hexdigest()


def load_source_scope(path: Path | str) -> SourceScope:
    """Load and validate an offline acquisition scope, such as ``sources.json``.

    A source scope approves where a later operator may acquire from.  It is not
    accepted by :func:`capture`, which requires a separate local capture manifest.
    """
    scope = _load_model(Path(path), SourceScope, "source scope")
    failures = _source_scope_failures(scope)
    if failures:
        raise CurationValidationError("; ".join(failures))
    return scope


def validate_source_scope(scope: SourceScope | Path | str) -> list[str]:
    """Return offline policy failures for an acquisition scope or its JSON path."""
    try:
        parsed = load_source_scope(scope) if isinstance(scope, (Path, str)) else scope
    except CurationValidationError as error:
        return [str(error)]
    return _source_scope_failures(parsed)


def load_manifest(path: Path | str) -> SourceManifest:
    """Load the separate pinned local capture manifest required by :func:`capture`."""
    return _load_model(Path(path), SourceManifest, "manifest")


def build_snapshot(manifest: SourceManifest, manifest_root: Path | str) -> Snapshot:
    """Read only local manifest inputs and construct a sorted content snapshot."""
    snapshot, _ = _build_snapshot_with_content(manifest, Path(manifest_root))
    return snapshot


def _build_snapshot_with_content(
    manifest: SourceManifest, root: Path
) -> tuple[Snapshot, dict[str, str]]:
    """Build a snapshot and retain the exact normalized bytes capture will write."""
    failures = _source_failures(manifest, root)
    if failures:
        raise CurationValidationError("; ".join(failures))
    records = []
    contents: dict[str, str] = {}
    for source in sorted(manifest.sources, key=lambda item: item.id):
        input_path = _safe_child(root, source.content_path)
        try:
            normalized = normalize_markdown(input_path.read_bytes())
        except UnicodeDecodeError as error:
            raise CurationValidationError(f"invalid UTF-8 content for {source.id}") from error
        contents[source.id] = normalized
        records.append(
            CorpusRecord(
                id=source.id,
                url=source.url,
                revision=source.revision,
                license=source.license,
                policy=source.policy,
                content_path=f"content/{source.id}.md",
                sha256=content_sha256(normalized),
                title=source.title,
            )
        )
    return Snapshot(records=records), contents


def capture(manifest_path: Path | str, output_root: Path | str) -> Snapshot:
    """Create a standalone local snapshot from a local approved manifest."""
    manifest_file = Path(manifest_path)
    manifest = load_manifest(manifest_file)
    snapshot, contents = _build_snapshot_with_content(manifest, manifest_file.parent)
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    for source in manifest.sources:
        record = next(item for item in snapshot.records if item.id == source.id)
        destination = _safe_child(root, record.content_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            contents[source.id],
            encoding="utf-8",
            newline="\n",
        )
    _write_artifacts(root, snapshot)
    return snapshot


def compare_records(baseline: list[CorpusRecord], candidate: list[CorpusRecord]) -> ChangeSet:
    """Classify records by ID and full record value in deterministic ID order."""
    old = {record.id: record for record in baseline}
    new = {record.id: record for record in candidate}
    return ChangeSet(
        added=[new[key] for key in sorted(new.keys() - old.keys())],
        changed=[new[key] for key in sorted(new.keys() & old.keys()) if new[key] != old[key]],
        removed=[old[key] for key in sorted(old.keys() - new.keys())],
        unchanged=[new[key] for key in sorted(new.keys() & old.keys()) if new[key] == old[key]],
    )


def refresh(
    snapshot_root: Path | str, manifest_path: Path | str, candidate_root: Path | str
) -> ChangeSet:
    """Capture a separate candidate root and write its deterministic changes file."""
    baseline = load_snapshot(Path(snapshot_root))
    candidate = capture(manifest_path, candidate_root)
    changes = compare_records(baseline.records, candidate.records)
    _write_json(Path(candidate_root) / "changes.json", changes.model_dump(mode="json"))
    return changes


def load_snapshot(root: Path | str) -> Snapshot:
    """Load a snapshot artifact from a corpus root."""
    return _load_model(Path(root) / "snapshot.json", Snapshot, "snapshot")


def validate_corpus(root: Path | str, *, require_approved: bool = False) -> list[str]:
    """Return all offline validation failures for a corpus artifact root."""
    root = Path(root)
    failures: list[str] = []
    snapshot = _try_load(root / "snapshot.json", Snapshot, "snapshot", failures)
    catalog = _try_load(root / "catalog.json", Catalog, "catalog", failures)
    review = _try_load(root / "review.json", ReviewArtifact, "review", failures)
    if snapshot is None or catalog is None or review is None:
        return failures
    failures.extend(_record_failures(snapshot.records, root))
    if snapshot.records != catalog.records:
        failures.append("catalog records do not match snapshot records")
    if review.snapshot_sha256 != _file_sha256(root / "snapshot.json"):
        failures.append("review snapshot hash mismatch")
    if review.catalog_sha256 != _file_sha256(root / "catalog.json"):
        failures.append("review catalog hash mismatch")
    expected_hashes = {record.id: record.sha256 for record in snapshot.records}
    if review.record_hashes != expected_hashes:
        failures.append("review record hashes do not match snapshot")
    if require_approved and not review.approved:
        failures.append("review is not approved")
    return failures


def require_valid_corpus(root: Path | str, *, require_approved: bool = False) -> None:
    """Raise when :func:`validate_corpus` detects an invalid corpus artifact."""
    failures = validate_corpus(root, require_approved=require_approved)
    if failures:
        raise CurationValidationError("; ".join(failures))


def _write_artifacts(root: Path, snapshot: Snapshot) -> None:
    catalog = Catalog(records=snapshot.records)
    _write_json(root / "snapshot.json", snapshot.model_dump(mode="json"))
    _write_json(root / "catalog.json", catalog.model_dump(mode="json"))
    review = ReviewArtifact(
        snapshot_sha256=_file_sha256(root / "snapshot.json"),
        catalog_sha256=_file_sha256(root / "catalog.json"),
        record_hashes={record.id: record.sha256 for record in snapshot.records},
    )
    _write_json(root / "review.json", review.model_dump(mode="json"))


def _source_scope_failures(scope: SourceScope) -> list[str]:
    failures: list[str] = []
    if scope.manifest_version <= 0:
        failures.append("manifest_version must be positive")
    if not scope.status.strip():
        failures.append("missing status")
    if not scope.sources:
        failures.append("empty source scope")
    source_ids = [source.id for source in scope.sources]
    if len(source_ids) != len(set(source_ids)):
        failures.append("duplicate source IDs")
    for source in scope.sources:
        if not _SAFE_ID.fullmatch(source.id):
            failures.append(f"unsafe source id: {source.id}")
        for field in (
            "identity",
            "owner",
            "access",
            "redistribution",
            "refresh_cadence",
            "document_status",
        ):
            if not str(getattr(source, field)).strip():
                failures.append(f"missing {field} for {source.id}")
        for field in ("canonical_url", "repository_url", "license_url"):
            if not _is_http_url(getattr(source, field)):
                failures.append(f"invalid {field} for {source.id}")
        if source.request_interval_seconds <= 0:
            failures.append(f"request_interval_seconds must be positive for {source.id}")
        if not source.path_scope.include:
            failures.append(f"empty include path scope for {source.id}")
        if not source.path_scope.exclude:
            failures.append(f"empty exclude path scope for {source.id}")
        for pattern in source.path_scope.include + source.path_scope.exclude:
            if not _is_safe_glob(pattern):
                failures.append(f"invalid path pattern for {source.id}: {pattern!r}")
        document_ids = [document.id for document in source.documents]
        if len(document_ids) != len(set(document_ids)):
            failures.append(f"duplicate document IDs for {source.id}")
        for document in source.documents:
            if not _SAFE_ID.fullmatch(document.id):
                failures.append(f"unsafe document id for {source.id}: {document.id}")
            if not _is_safe_glob(document.path):
                failures.append(f"invalid document path for {source.id}: {document.path!r}")
            if not _is_http_url(document.url):
                failures.append(f"invalid document URL for {source.id}: {document.id}")
            if not document.provenance.strip():
                failures.append(f"missing document provenance for {source.id}: {document.id}")
            if _is_unpinned_revision(document.revision):
                failures.append(f"unpinned document revision for {source.id}: {document.id}")
    return failures


def _is_http_url(value: str) -> bool:
    """Return whether a nonblank value is an absolute HTTP(S) URL."""
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _is_safe_glob(pattern: str) -> bool:
    """Accept a nonempty repository-relative glob without traversal components."""
    path = Path(pattern)
    return bool(
        pattern.strip()
        and "\\" not in pattern
        and "\x00" not in pattern
        and not path.is_absolute()
        and "" not in pattern.split("/")
        and not any(part in {"", ".", ".."} for part in path.parts)
        and pattern.count("[") == pattern.count("]")
    )


def _is_unpinned_revision(revision: str) -> bool:
    """Return whether revision is blank or a known moving reference."""
    return not revision.strip() or revision.strip().lower() in _FLOATING_REVISIONS


def _source_failures(manifest: SourceManifest, root: Path) -> list[str]:
    failures = _record_metadata_failures(manifest.sources)
    for source in manifest.sources:
        try:
            path = _safe_child(root, source.content_path)
            if not path.is_file():
                failures.append(f"missing content file for {source.id}: {source.content_path}")
        except CurationValidationError as error:
            failures.append(f"unsafe content path for {source.id}: {error}")
    return failures


def _record_failures(records: list[CorpusRecord], root: Path) -> list[str]:
    failures = _record_metadata_failures(records)
    for record in records:
        try:
            path = _safe_child(root, record.content_path)
            if not path.is_file():
                failures.append(f"missing content file for {record.id}: {record.content_path}")
            elif content_sha256(path.read_bytes()) != record.sha256:
                failures.append(f"content hash mismatch for {record.id}")
        except (CurationValidationError, UnicodeDecodeError) as error:
            failures.append(f"broken content for {record.id}: {error}")
    return failures


def _record_metadata_failures(records: list[Any]) -> list[str]:
    failures: list[str] = []
    for attr, label in (("id", "IDs"), ("url", "URLs")):
        values = [getattr(record, attr) for record in records]
        if len(values) != len(set(values)):
            failures.append(f"duplicate {label}")
    hashes = [getattr(record, "sha256", None) for record in records]
    known_hashes = [value for value in hashes if value]
    if len(known_hashes) != len(set(known_hashes)):
        failures.append("duplicate content hashes")
    for record in records:
        if not _SAFE_ID.fullmatch(record.id):
            failures.append(f"unsafe id: {record.id}")
        if not _is_http_url(record.url):
            failures.append(f"invalid URL for {record.id}")
        if not all(
            str(getattr(record, field, "")).strip() for field in ("revision", "license", "policy")
        ):
            failures.append(f"incomplete provenance or policy for {record.id}")
        if _is_unpinned_revision(str(record.revision)):
            failures.append(f"unpinned revision for {record.id}")
    return failures


def _safe_child(root: Path, relative: str) -> Path:
    path = Path(relative)
    if path.is_absolute() or not relative or any(part in {"", ".", ".."} for part in path.parts):
        raise CurationValidationError("path is not a safe relative path")
    resolved_root = root.resolve()
    resolved = (resolved_root / path).resolve()
    if not resolved.is_relative_to(resolved_root):
        raise CurationValidationError("path escapes root")
    return resolved


def _load_model(path: Path, model: type[BaseModel], label: str) -> Any:
    try:
        return model.model_validate_json(path.read_bytes())
    except (OSError, ValidationError, ValueError) as error:
        raise CurationValidationError(f"invalid {label}: {error}") from error


def _try_load(path: Path, model: type[BaseModel], label: str, failures: list[str]) -> Any | None:
    try:
        return _load_model(path, model, label)
    except CurationValidationError as error:
        failures.append(str(error))
        return None


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )


def _file_sha256(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return ""
