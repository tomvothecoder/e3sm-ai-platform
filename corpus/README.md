# Corpus curation scope

`sources.json` is the human-owned, initially approved acquisition scope for
official E3SM documentation. It is not the capture manifest consumed by
`backend/scripts/corpus.py`; its empty document lists intentionally state that
no documents have been selected, captured, or reviewed.

For capture, derive a separate local capture manifest from this scope. That
file-backed manifest names selected local inputs and pins each upstream revision
before it is passed to the curation CLI. Before publication, each selected
document requires that manifest, a raw snapshot, normalization, and reviewer
approval. Keep the two manifest types and acquisition outputs separate:

```text
corpus/
  sources.json       # human-owned approved scope; no captured documents
  capture-manifest.json # local, pinned selection for the curation CLI
  snapshots/         # pinned, raw acquisition snapshots (not yet populated)
  markdown/          # normalized, approved Markdown (not yet populated)
```

See [corpus curation](../docs/dev/corpus-curation.md) for the offline workflow.
