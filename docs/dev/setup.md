# Developer setup

This guide describes repository setup and validation commands for the current
prototype.

## Prerequisites

- Python 3.13.
- `uv` for the Python workspace.
- Node.js and npm for the frontend package.
- Docker Desktop only if using the optional local observability stack.

## Python workspace

The root `pyproject.toml` defines a `uv` workspace with `backend` and
`evaluation` members. Install Python dependencies from the repository root:

```bash
uv sync --all-packages --all-groups
```

Run the backend:

```bash
uv run --all-packages --directory backend uvicorn e3sm_assist.app:app --reload
```

Run backend tests:

```bash
make backend-test
```

Run the deterministic integration evaluation against the packaged backend
adapter:

```bash
make evaluation-test
```

The Makefile expands that target to:

```bash
E3SM_ASSIST_EVALUATOR=e3sm_assist.evaluation_adapter:evaluate uv run --all-packages pytest evaluation
```

## Frontend package

Install frontend dependencies:

```bash
npm --prefix frontend ci
```

Start the Vite development server:

```bash
npm --prefix frontend run dev
```

Frontend validation targets are available through Make:

```bash
make frontend-test frontend-lint frontend-typecheck frontend-build
```

The package scripts are `test`, `lint`, `typecheck`, and `build`.

## Local configuration

Backend settings are read from environment variables and optional `backend/.env`.
Common local settings are:

- `E3SM_ASSIST_CORS_ALLOW_ORIGINS`: comma-separated browser origins allowed by
  FastAPI CORS; defaults to `http://localhost:5173`.
- `ASSISTANT_GENERATOR`: `deterministic` by default; set to `livai` only with a
  configured backend API key.
- `ASSISTANT_LIVAI_API_KEY`, `ASSISTANT_LIVAI_MODEL`,
  `ASSISTANT_LIVAI_BASE_URL`: backend-only LivAI settings.
- `E3SM_ASSIST_OTLP_ENDPOINT`, `E3SM_ASSIST_SERVICE_NAME`,
  `E3SM_ASSIST_DEPLOYMENT_ENVIRONMENT`, `E3SM_ASSIST_OTLP_HEADERS`: optional
  backend observability settings.
- `E3SM_ASSIST_RETRIEVAL_MODE`: `lexical` (default), `semantic`, or `hybrid`.
  Lexical mode is offline-safe and never loads an embedding model.
- `E3SM_ASSIST_EMBEDDING_MODEL`: Hugging Face model used for semantic and hybrid
  retrieval; defaults to `BAAI/bge-small-en-v1.5`. Starting either mode may
  download the model and its dependencies on first use, so provision network
  access, cache storage, and suitable CPU or accelerator memory for the chosen
  model.
- `E3SM_ASSIST_RETRIEVAL_SEMANTIC_MIN_SCORE`: dense cosine-similarity gate for
  semantic evidence; defaults to `0.7`. It is a model-calibration threshold,
  not a confidence percentage.
- `E3SM_ASSIST_RETRIEVAL_LEXICAL_MIN_COVERAGE` and
  `E3SM_ASSIST_RETRIEVAL_LEXICAL_MIN_SCORE`: lexical acceptance gates, defaulting
  to `0.18` and `0.11` respectively.
- `E3SM_ASSIST_RETRIEVAL_LEXICAL_WEIGHT` and
  `E3SM_ASSIST_RETRIEVAL_SEMANTIC_WEIGHT`: non-negative hybrid weights, each
  defaulting to `0.5`. Hybrid ranking uses their normalized weighted average of
  lexical relevance (clamped lexical score) and non-negative semantic cosine
  similarity. Set at least one weight above zero.

For example, enable semantic retrieval locally with:

```bash
E3SM_ASSIST_RETRIEVAL_MODE=semantic \
E3SM_ASSIST_EMBEDDING_MODEL=BAAI/bge-small-en-v1.5 \
E3SM_ASSIST_RETRIEVAL_SEMANTIC_MIN_SCORE=0.7 \
uv run --all-packages --directory backend uvicorn e3sm_assist.app:app --reload
```

Semantic and hybrid candidates still require official source authority and are
rejected for unsupported intents. They retain citations and produce the same
explicit insufficient-evidence response when no acceptable evidence is found.

Frontend local settings are documented in `frontend/.env.example`:

- `VITE_API_BASE_URL`: leave empty for local development through the Vite proxy.
- `VITE_DEV_API_PROXY_TARGET`: backend target for proxied `/query` calls;
  defaults to `http://localhost:8000`.

Do not expose backend secrets through `VITE_` variables.

## Validation commands

Repository guidance requires Ruff and ty for Python validation:

```bash
uv run --all-packages ruff format backend evaluation
uv run --all-packages ruff check backend evaluation
uv run --all-packages ty check
```

The Makefile also provides current mypy targets:

```bash
make backend-typecheck
make evaluation-typecheck
```

`make check` currently runs backend tests, backend Ruff lint, backend mypy,
evaluation tests, evaluation Ruff lint, and evaluation mypy. It does not run the
frontend checks or `ty check`.

Optional full pre-commit validation from repository guidance:

```bash
uv run --all-packages pre-commit run --all-files
```

## Observability stack

The local Docker Collector and Jaeger stack is optional and developer-only:

```bash
make observability-up
make observability-status
make observability-logs
make observability-down
```

Configuration details and telemetry payload rules are canonical in
[observability.md](observability.md).
