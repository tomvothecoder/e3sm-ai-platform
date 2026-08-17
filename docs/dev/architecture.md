# Architecture

The current repository is a minimal vertical slice for E3SM-ASSIST. It favors
deterministic, provider-independent boundaries over a larger application
framework.

## Repository layout

- `backend/`: FastAPI service package `e3sm_assist`.
- `frontend/`: React, TypeScript, and Vite chat UI.
- `evaluation/`: independent deterministic pytest integration evaluation.
- `docs/`: canonical guides, status, roadmap, and historical prompt.

The root Python workspace includes `backend` and `evaluation`. The frontend is a
separate npm package.

## Backend flow

`POST /query` is implemented by the FastAPI app in `e3sm_assist.app`. The
application service wires these stages:

1. Load the bundled static curated corpus JSON.
2. Chunk entries deterministically while preserving citation metadata.
3. Retrieve lexical, semantic, or hybrid candidates with an in-memory store.
4. Filter accepted curated evidence separately from raw candidates.
5. Select a deterministic route.
6. Generate either an evidence-constrained answer or an explicit
   insufficient-evidence response.

`GET /health` returns service status, corpus summary information, and chunk
count.

## Corpus and retrieval

The bundled corpus currently contains 31 curated official-source records covering
the E3SM User Guide, Running E3SM, EAM, EAMxx, ELM, E3SM Diagnostics, and
E3SM-Unified. Each record retains source ID, title, URL, section, component,
version, authority, provenance, and text.

Retrieval defaults to deterministic, local lexical term-frequency vectors. This
offline-safe mode does not initialize or download an embedding model. Its
scoring, metadata bonuses, phrase bonuses, and acceptance policy require
meaningful query coverage, score, and official authority. A deterministic
LlamaIndex-backed lexical store also exists as an optional in-memory
implementation.

Set `E3SM_ASSIST_RETRIEVAL_MODE` to `semantic` or `hybrid` to enable dense
retrieval through `llama-index-embeddings-huggingface`. The service constructs
the configured `E3SM_ASSIST_EMBEDDING_MODEL` only in those modes; it defaults to
`BAAI/bge-small-en-v1.5`. The model is downloaded by Hugging Face on its first
use unless already cached. Tests inject a `SemanticEmbedder` rather than loading
a model.

Raw candidate evidence may appear in debug metadata for gap responses, but it is
labeled unverified and is not returned as accepted evidence or citations.

## Candidate ranking and evidence acceptance

The default `InMemoryVectorStore` retrieves up to `max(top_k, 8)` candidates,
sorts them by descending score, and uses `chunk_id` to break score ties
deterministically. `top_k` defaults to 4. Semantic and hybrid modes retain the
same tie-breaker and source metadata.

Each candidate score is composed of:

```text
cosine similarity
+ (query-term coverage x 0.45)
+ metadata matches (0.035 each)
+ targeted phrase bonuses
```

Query-term coverage is the share of normalized, expanded query terms found in a
candidate's source ID, title, section, component, or text. Normalization removes
common stopwords, and a small synonym map expands related terms such as
`compset` and `compsets`.

A candidate is accepted as curated evidence only when it has official authority,
coverage of at least `0.18`, and a score of at least `0.11`. Requests matching
unsupported-intent phrases accept no evidence. To keep an answer coherent, an
accepted candidate must share a matched term with the top accepted candidate,
unless it has coverage of at least `0.34`. The final accepted set is capped at
the requested `top_k`.

Semantic mode ranks by dense cosine similarity. It can accept an official
paraphrase with low lexical coverage only when `semantic_score` meets
`E3SM_ASSIST_RETRIEVAL_SEMANTIC_MIN_SCORE` (default `0.7`). Hybrid mode computes
the deterministic weighted average below, where lexical relevance is the
lexical score clamped to `[0, 1]` and semantic relevance is cosine similarity
clamped at zero:

```text
hybrid_score = (
  lexical_weight * clamp(lexical_score, 0, 1)
  + semantic_weight * max(semantic_score, 0)
) / (lexical_weight + semantic_weight)
```

The weights default to `0.5` each and are configured with
`E3SM_ASSIST_RETRIEVAL_LEXICAL_WEIGHT` and
`E3SM_ASSIST_RETRIEVAL_SEMANTIC_WEIGHT`. Hybrid acceptance permits either the
existing lexical gate or the calibrated semantic threshold, but never bypasses
official authority, unsupported-intent rejection, citation provenance, or
explicit insufficient-evidence behavior. The lexical thresholds remain
configurable as `E3SM_ASSIST_RETRIEVAL_LEXICAL_MIN_COVERAGE` and
`E3SM_ASSIST_RETRIEVAL_LEXICAL_MIN_SCORE`.

The router selects the `curated` path only when accepted evidence exists and its
top score is at least `0.12`. Otherwise, routing rules may select an explicit
insufficient-evidence, web, or future operational path.

### Evidence metadata and score display

Every evidence record includes `retrieval_mode`, `score`, `lexical_score`,
`semantic_score`, and `coverage` where applicable. Scores are relevance values,
not probabilities or confidence percentages. The frontend displays the primary
value as a retrieval score and labels `coverage * 100` as lexical coverage; for
example, 67% coverage means that two-thirds of the normalized query terms appear
in the evidence.

## Routing and generation

The exposed route values are:

- `curated`: accepted curated evidence supports the answer.
- `web`: the question appears to require current web information.
- `future_operational`: the question appears to require live operational,
  GitHub, SimBoard, scheduler, or tool data.
- `insufficient_evidence`: no accepted curated evidence is available, or the
  query is unsupported.

The prototype does not include a live web-search provider or live operational
connector. Those routes currently produce explicit insufficient-evidence
messages.

Generation is deterministic by default and cites only accepted curated evidence.
Optional LivAI generation can be enabled for curated-evidence answers with
backend-only environment variables; provider errors fall back to deterministic
generation.

## API response shape

The canonical response includes:

- `answer`
- `route`
- `route_alias`
- `citations`
- `evidence`
- `retrieved_evidence`
- `insufficient_evidence`
- `debug`

`retrieved_evidence` is the flat evaluation-compatible field. Each record carries
source and provenance data needed to connect evidence to citations.

## Frontend

The frontend is a React/Vite chat UI with question input, answer display,
citations, loading/error states, expandable evidence, and route/source debug
display. In local development, Vite proxies `/query` to the backend unless
`VITE_API_BASE_URL` is configured.

The browser sends W3C `traceparent` headers for query requests and displays the
server-generated `X-Request-ID` in generic error messages when available.

## Extension boundaries

Provider-independent protocols exist for:

- embedders;
- vector stores;
- rerankers;
- hybrid retrievers;
- future web sources;
- future operational/tool sources.

These boundaries are intended to support later pgvector, hybrid retrieval,
reranking, web search, SimBoard, GitHub/API/MCP, and other tool integrations
without changing the deterministic evaluation baseline.

## Current non-goals and gaps

The current prototype does not implement authentication, authorization,
persistent conversation history, live web retrieval, live operational tools,
write-capable tools, production telemetry deployment, metrics export, log export
through OpenTelemetry, or production audit logging.

For observability details and future operating requirements, see
[observability.md](observability.md).
