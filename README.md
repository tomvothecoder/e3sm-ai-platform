# E3SM AI Platform

An extensible, provider-independent prototype for **E3SM-ASSIST**: a chat interface
for answering E3SM questions from curated, authoritative documentation. It favors
traceable evidence and explicit uncertainty over unsupported answers.

## Setup

Prerequisites: Python 3.13, [uv](https://docs.astral.sh/uv/), and Node.js 22 with
npm. Install the Python workspace once from the repository root:

```bash
uv sync --all-packages --all-groups
(cd frontend && npm ci)
```

Run locally:

```bash
uv run --all-packages --directory backend uvicorn e3sm_assist.app:app --reload
(cd frontend && npm run dev)
```

The backend defaults to local curated-corpus data. No proprietary service or
network request is required to run or test the prototype.

### Optional local tracing

Local trace inspection uses Docker Desktop plus the development Collector and
Jaeger stack expected at `deploy/observability/docker-compose.yml`:

```bash
make observability-up
E3SM_ASSIST_OTLP_ENDPOINT=http://localhost:4318/v1/traces \
E3SM_ASSIST_SERVICE_NAME=e3sm-assist-backend \
E3SM_ASSIST_DEPLOYMENT_ENVIRONMENT=local \
uv run --all-packages --directory backend uvicorn e3sm_assist.app:app --reload
```

Submit a query, then open Jaeger at <http://localhost:16686>. The local stack is
for loopback-only development metadata under the privacy rules in the
[observability guide](docs/dev/observability.md). Stop it with
`make observability-down`; that target is expected to stop containers without a
volume-deletion flag, but local Jaeger traces may still be ephemeral depending on
the compose storage configuration.

### Optional LivAI generation

Deterministic generation is the default. To enable the optional LivAI generator for
answers supported by curated evidence, set these **backend-only** environment
variables (for example, in `backend/.env` or in the backend process environment):

```bash
ASSISTANT_GENERATOR=livai
ASSISTANT_LIVAI_API_KEY=your-secret-key
ASSISTANT_LIVAI_MODEL=gpt-5.5
ASSISTANT_LIVAI_BASE_URL=https://livai-api.llnl.gov/
```

`ASSISTANT_LIVAI_API_KEY` is a secret and must be injected through an untracked
backend environment or `backend/.env`, or through a deployment secret manager; it
must not be committed. These variables are not `VITE_` variables and must never be
placed in frontend configuration. The configured endpoint must use HTTPS; a
misconfigured or non-HTTPS endpoint is rejected. LivAI requests use a 30-second
timeout and have no automatic retry. LivAI is only used after curated evidence
supports the answer; routing and evidence selection remain local. If a request fails,
the backend falls back to deterministic evidence-constrained output rather than making
a runtime web request.

## Architecture

- `frontend/` is a React + TypeScript + Vite chat client.
- `backend/` contains the FastAPI `POST /query` vertical slice and independently
  testable ingestion, retrieval, routing, generation, and integration interfaces.
- `evaluation/` contains deterministic question fixtures and scoring checks.
- The [observability guide](docs/dev/observability.md) describes the current
  baseline and future telemetry, audit, and RAG reproducibility requirements.
- This root `pyproject.toml` defines a uv workspace over the backend and evaluation
  Python projects; their dependency declarations remain owned by those projects.

The query response exposes the selected route and retrieved evidence to support the
client debug view and automated evaluation. Provider interfaces leave room for local
or hosted embeddings, vector stores, generation models, and operational connectors
without coupling the core flow to any vendor.

## Ingestion

Curated source records retain the source URL, section, component/topic, version,
authority, and provenance. Ingestion normalizes those records, splits them into
attributable chunks, creates embeddings through an abstraction, and stores them in a
retrieval backend. The starter corpus is deliberately local and representative of
the E3SM User Guide, Running E3SM Guide, EAM/EAMxx, ELM, diagnostics, and
E3SM-Unified material. Refreshing or expanding corpus content is an explicit ingest
operation, not a runtime web fetch.

## Routing

Each question is routed deterministically among:

1. **Curated RAG** for supported, stable documentation questions.
2. **Web-search fallback** only when configured and a current-information or corpus
   gap route is selected.
3. **Operational/tool source** through future SimBoard, GitHub, API, or MCP adapters.
4. **Insufficient evidence** when available sources cannot support a reliable answer.

Answers include citations and evidence. The insufficient-evidence path must say what
is missing rather than infer facts. Networked fallback integrations are opt-in and
are not invoked by default.

## Evaluation

The evaluation suite uses representative E3SM questions to score route correctness,
retrieval relevance, citation/provenance presence, and insufficient-evidence
behavior. It is deterministic and uses fixtures rather than live LLM or web calls.

```bash
make backend-test backend-lint backend-typecheck evaluation-test evaluation-lint evaluation-typecheck
make frontend-install frontend-test frontend-lint frontend-typecheck frontend-build
```

The CI workflow runs these Python checks in `backend/` and `evaluation/`, and runs
frontend install, test, lint, typecheck, and production build explicitly in
`frontend/`.

## Limitations

- The prototype corpus is small and not a complete substitute for current E3SM docs.
- Retrieval quality is bounded by chunking, corpus coverage, and the selected local
  embedding implementation.
- Web and operational connectors are extension points, not bundled credentials or
  live production integrations.
- LivAI generation is optional and requires a backend-only API key; deterministic
  generation remains the no-secret default.
- It has no authentication, persistent conversation history, or access controls.

## Next steps

1. Expand and version the curated corpus with a reviewed update process.
2. Add hybrid retrieval, reranking, and pgvector behind existing interfaces.
3. Implement permission-aware SimBoard, GitHub MCP, and operational API adapters.
4. Add regression fixtures from real user questions and review citation quality.
5. Add deployment configuration, observability, authentication, and data governance
   before handling protected operational data.
