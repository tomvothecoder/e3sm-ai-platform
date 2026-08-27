# E3SM AI Platform documentation

This directory is the documentation entry point for the current E3SM AI Platform
prototype, focused on E3SM-ASSIST.

## Canonical guides

- [User usage guide](user/usage.md): run the prototype locally and submit
  assistant questions.
- [Developer setup](dev/setup.md): install dependencies, configure local
  services, and run validation commands.
- [Architecture](dev/architecture.md): current backend, frontend, retrieval,
  routing, generation, and extension boundaries.
- [Evaluation](dev/evaluation.md): deterministic integration evaluation and the
  adapter contract.
- [Roadmap](roadmap.md): planned implementation areas and known gaps.
- [Observability](dev/observability.md): canonical observability guidance and
  local tracing workflow.
- [Corpus curation](dev/corpus-curation.md): approved acquisition scope and
  offline operator workflow; no runtime integration yet.

## Status and historical documents

- [Prototype status](dev/prototype-status.md): delivered feature/status claims
  and verification evidence only.
- [Original prompt](dev/prompt.md): historical, non-canonical initial
  specification retained for context.

## Repository areas

- `backend/`: FastAPI E3SM-ASSIST service and packaged evaluator adapter.
- `frontend/`: React, TypeScript, and Vite chat UI.
- `evaluation/`: independent deterministic pytest suite for response-contract
  checks.
