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
3. Retrieve lexical candidates with an in-memory store.
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

Retrieval is deterministic and local. The default store uses lexical
term-frequency vectors, scoring, metadata bonuses, phrase bonuses, and an
acceptance policy requiring meaningful query coverage, score, and official
authority. A deterministic LlamaIndex-backed lexical store also exists as an
optional in-memory implementation.

Raw candidate evidence may appear in debug metadata for gap responses, but it is
labeled unverified and is not returned as accepted evidence or citations.

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
