# E3SM-ASSIST prototype status

## Delivered

- Python 3.13 `uv` workspace with separate `backend/`, `frontend/`, and `evaluation/` packages.
- FastAPI `POST /query` service with deterministic ingestion, chunking, lexical retrieval, evidence-constrained generation, citations, provenance, and debug information.
- A curated 30-entry corpus covering the E3SM User Guide, Running E3SM, EAM, EAMxx, ELM, E3SM Diagnostics, and E3SM-Unified.
- Deterministic route selection: curated documentation, web-search fallback, future operational/tool source, and explicit insufficient-evidence responses.
- Provider-independent interfaces for embedders, stores, rerankers, hybrid retrieval, web sources, and operational sources; constructor injection allows replacement without a framework.
- Evaluation-compatible response fields (`route`, `retrieved_evidence`, citation provenance) and a packaged evaluator at `e3sm_assist.evaluation_adapter:evaluate`.
- React/Vite chat UI with loading/error states, citations, expandable evidence, and a debug route/source view.
- Local integration support through the Vite `/query` proxy and configurable FastAPI CORS (`E3SM_ASSIST_CORS_ALLOW_ORIGINS`).
- Optional backend-only LivAI generation configuration for curated-evidence answers, with deterministic fallback if the provider is unavailable.
- GitHub Actions for backend, evaluation, and frontend checks.

## Evidence and verification

- Backend: 28 pytest tests, Ruff, and strict mypy passed.
- Evaluation: 35 deterministic checks passed: 20 route/retrieval, 12 citation/provenance, and 3 insufficient-evidence cases. The suite runs with `E3SM_ASSIST_EVALUATOR=e3sm_assist.evaluation_adapter:evaluate`.
- Frontend: 2 Vitest tests, ESLint, TypeScript type checking, and a production Vite build passed.
- Backend startup import was validated with `e3sm_assist.app:app`.
- One non-blocking upstream warning remains: Starlette's `TestClient` deprecation notice for its current `httpx` integration.

## Review outcomes

Oracle and independent review identified and the implementation resolved:

- overly broad retrieval and substring routing matches;
- raw candidate evidence being presented as accepted support;
- evaluation DTO and source-ID mismatches;
- invalid workspace/CI evaluation execution;
- frontend nested-evidence rendering and local cross-origin connectivity; and
- noncanonical E3SM-Unified documentation URLs.

Raw retrieval candidates, when returned in debug metadata, are explicitly labeled unverified and are never presented as accepted evidence or citations.

## Run commands

```bash
uv sync --all-packages --all-groups
uv run --all-packages --directory backend uvicorn e3sm_assist.app:app --reload

# In another terminal
(cd frontend && npm ci && npm run dev)
```

Run all Python checks with `make check`; run frontend checks with `make frontend-test frontend-lint frontend-typecheck frontend-build`.

### Optional LivAI configuration

Deterministic generation remains the default. To opt into LivAI for answers that
already have curated supporting evidence, configure the backend process only:

```bash
ASSISTANT_GENERATOR=livai
ASSISTANT_LIVAI_API_KEY=your-secret-key
ASSISTANT_LIVAI_MODEL=gpt-5.5
ASSISTANT_LIVAI_BASE_URL=https://livai-api.llnl.gov/
```

Inject the API key through an untracked backend environment or `backend/.env`, or
through a deployment secret manager; never commit it. Do not use `VITE_` names or
expose these values to the frontend. The endpoint must use HTTPS; a misconfigured or
non-HTTPS endpoint is rejected. Requests use a 30-second timeout with no automatic
retry. Provider errors fall back to deterministic evidence-constrained output; they do
not trigger runtime web retrieval.

## Next steps

1. Replace the in-memory lexical store with pgvector and add hybrid retrieval plus reranking; retain deterministic tests as the regression baseline.
2. Build an approved web-search provider and normalize returned web citations before enabling live fallback responses.
3. Implement authenticated SimBoard, GitHub MCP, and other operational connectors; add authorization, audit logging, and tool-result provenance before exposing them.
4. Expand the curated corpus with versioned source snapshots, automated ingestion, freshness checks, and human relevance review.
5. Add release-oriented evaluation: larger question sets, retrieval metrics, routing confusion reports, answer/citation quality review, and regression thresholds in CI.
6. Add optional conversational context only after defining retention, privacy, and evidence-isolation rules.
7. Generalize application registration for additional E3SM assistants without coupling their corpus, prompts, tools, or evaluation sets.
8. Establish approved secret provisioning and observability for optional LivAI use before enabling it outside controlled environments.
