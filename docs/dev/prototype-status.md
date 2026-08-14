# E3SM-ASSIST prototype status

This document is limited to current status and evidence. For setup, usage,
architecture, evaluation, observability, and roadmap guidance, use the canonical
guides linked from [../README.md](../README.md).

## Delivered status

- Python 3.13 `uv` workspace with `backend` and `evaluation` members, plus a
  separate React/Vite frontend package.
- FastAPI `POST /query` service with deterministic ingestion, chunking, lexical retrieval, evidence-constrained generation, citations, provenance, and debug information.
- A curated 31-entry corpus covering the E3SM User Guide, Running E3SM, EAM, EAMxx, ELM, E3SM Diagnostics, and E3SM-Unified.
- Deterministic route selection: curated documentation, web-information-needed,
  future operational/tool-data-needed, and explicit insufficient-evidence
  responses.
- Provider-independent interfaces for embedders, stores, rerankers, hybrid retrieval, web sources, and operational sources; constructor injection allows replacement without a framework.
- Evaluation-compatible response fields (`route`, `retrieved_evidence`, citation provenance) and a packaged evaluator at `e3sm_assist.evaluation_adapter:evaluate`.
- React/Vite chat UI with loading/error states, citations, expandable evidence, and a debug route/source view.
- Local integration support through the Vite `/query` proxy and configurable FastAPI CORS (`E3SM_ASSIST_CORS_ALLOW_ORIGINS`).
- Optional backend-only LivAI generation configuration for curated-evidence answers, with deterministic fallback if the provider is unavailable.

## Not delivered

- Live web-search provider execution; the `web` route currently returns an
  explicit insufficient-evidence response.
- Live SimBoard, GitHub, scheduler, MCP, or other operational/tool connectors;
  the `future_operational` route currently returns an explicit
  insufficient-evidence response.
- Authentication, authorization, persistent conversation history, write-capable
  tools, production telemetry deployment, metrics export, OpenTelemetry log
  export, or production audit logging.

## Evidence and verification

- Backend verification is covered by pytest, Ruff, and mypy targets in the
  Makefile; see [setup.md](setup.md) for canonical validation guidance.
- Evaluation verification is covered by deterministic pytest checks run with
  `E3SM_ASSIST_EVALUATOR=e3sm_assist.evaluation_adapter:evaluate`.
- Frontend verification is covered by Vitest, ESLint, TypeScript type checking,
  and production Vite build targets in the Makefile.
- Backend startup target is `e3sm_assist.app:app`.
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
