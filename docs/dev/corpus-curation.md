# Corpus curation

Phase 2 defines an operator-managed acquisition scope only. It has no runtime
impact until Phase 3. Tests and CI perform no live source checks.

The human-owned approved scope is
[`corpus/sources.json`](../../corpus/sources.json). It records approved sources,
license references, rate limits, and candidate path scopes. Its empty document
lists intentionally mean that no documents have been selected, captured, or
reviewed.

This source scope is not the manifest accepted by `backend/scripts/corpus.py`.
For each capture, an operator derives a separate local capture manifest from the
scope. The capture manifest is file-backed: it selects local input files and
pins the upstream revision and source metadata for every selected document.
Do not pass `corpus/sources.json` to `capture` or `refresh`.

## Workflow

1. **Capture:** select paths within the source scope, create a pinned local
   capture manifest, and save the local inputs and resulting artifacts.
2. **Offline refresh:** use the saved snapshot and another local, pinned capture
   manifest to write a separate candidate corpus; do not fetch live URLs.
3. **Reviewer approval:** verify source identity, pinned revision, license and
   attribution requirements, scope, and normalized content. Record approval in
   the generated review artifact.
4. **Validate:** validate manifest JSON and offline snapshot/Markdown metadata;
   do not fetch sources during validation.

Do not publish a document without a pinned revision, raw snapshot, normalized
copy, and reviewer approval.

## Commands

Run these from the repository root. Paths below are operator-local examples.

```bash
# Validate the checked-in human-owned source scope (command planned for Phase 2).
uv run --package e3sm-assist-backend python backend/scripts/corpus.py validate-sources corpus/sources.json

# Capture selected local files named by a pinned local capture manifest.
uv run --package e3sm-assist-backend python backend/scripts/corpus.py capture /path/to/capture-manifest.json /path/to/current-corpus

# Build a separate offline candidate from a current snapshot and local manifest.
uv run --package e3sm-assist-backend python backend/scripts/corpus.py refresh /path/to/current-corpus /path/to/capture-manifest.json /path/to/candidate-corpus

# Validate corpus artifacts and require hash-bound reviewer approval.
uv run --package e3sm-assist-backend python backend/scripts/corpus.py validate /path/to/candidate-corpus --require-approved
```
