# AGENTS.md — Canonical AI Development Rules

This file is the source of truth for AI-assisted development in this repository.
Tool-specific instructions may add constraints, but must not contradict it.

## Anti-drift policy

This repository is actively evolving. Treat its source, manifests, lockfiles,
CI workflows, and documentation as the current authority; do not rely on a
snapshot of the project structure or dependency versions.

- Do not hardcode dependency versions, test counts, CI matrix values, or other
  volatile details in instruction files.
- Read the relevant implementation and configuration before making structural
  changes. Preserve existing behavior unless the task explicitly changes it.
- Keep changes scoped. Do not bundle broad cleanup, speculative abstractions, or
  unrelated renames with a feature or defect fix.
- Update tests, user-facing documentation, and developer documentation when a
  change affects behavior, configuration, commands, or public contracts.

## Product and repository boundaries

- **E3SM AI Platform** is the repository and backend platform.
- **E3SM Compass** is the assistant-facing product, including UI text, API
  titles, prompt identity, and evaluation contract.
- Use `e3sm_ai_platform` for Python package identifiers and unprefixed backend
  configuration variables. Use `E3SM_COMPASS_EVALUATOR` for the external
  evaluation adapter contract.

## Architecture

### Repository layout

- `backend/` — FastAPI backend package, tests, and offline curation scripts.
- `backend/src/e3sm_ai_platform/` — backend source package.
- `frontend/` — React, TypeScript, and Vite client.
- `evaluation/` — black-box E3SM Compass response-contract checks.
- `docs/` — user, developer, architecture, and operational guidance.
- `deploy/` — local observability configuration.

### Backend boundaries

- Keep HTTP wiring in `api/`; it should not own application behavior.
- Keep orchestration in `application/`, domain contracts in `domain/`, curated
  corpus and retrieval concerns in `knowledge/`, and runtime adapters in
  `infrastructure/` or `integrations/`.
- Keep the evaluation adapter independent of FastAPI app construction and
  observability initialization.
- Treat the curated corpus as packaged data. Do not fetch documentation during
  request handling or commit generated local retrieval artifacts.
- Preserve the evidence-first response contract: cite accepted evidence and
  return an explicit insufficient-evidence response when support is unavailable.

## Coding standards

### Python and backend

- Use `uv` for Python commands and dependency management; do not use `pip` or
  create ad hoc virtual environments in the repository.
- Use Ruff as the formatter and linter, and `ty` as the only Python type checker.
- New or modified public modules, classes, and functions need NumPy-style
  docstrings. Do not add unrelated docstrings to untouched legacy code.
- Group imports, setup, core logic, and result construction with logical blank
  lines. Use two blank lines between top-level definitions.
- Keep public types and functions together near the top of a module, ordered by
  the user-facing workflow. Prefix implementation-only helpers with `_`.
- Preserve final newlines. Add a blank line before a final `return` only when it
  separates completed computation from the returned result.

### Frontend

- Use npm and the scripts defined in `frontend/package.json`.
- Keep UI behavior accessible and evidence-oriented: loading and error states,
  citations, and insufficient-evidence responses must remain understandable.
- Keep API contract changes synchronized with frontend types and tests.

## Testing and validation

Agents may run repository QA tools without requesting permission.

- Use focused checks while diagnosing a concrete change or failure.
- Run the full formatting, lint, type, test, and pre-commit suite once at final
  integration verification rather than after every incremental edit.
- Run all commands from the repository root. `make help` lists supported local
  workflows and is the preferred entry point for targeted checks.
- The authoritative Python validation commands are:

  ```bash
  uv run --all-packages ruff format backend evaluation
  uv run --all-packages ruff check backend evaluation
  uv run --all-packages ty check
  uv run --all-packages pre-commit run --all-files
  ```

- Run backend tests for backend changes, frontend tests and build checks for
  frontend changes, and the evaluation suite when changing the E3SM Compass
  response contract.

## Dependency and configuration policy

- Declare Python dependencies in the applicable `pyproject.toml` and refresh
  `uv.lock` through `uv`; declare frontend dependencies in `frontend/package.json`
  and update its lockfile through npm.
- Do not add dependencies unless the existing platform capabilities are
  insufficient and the added dependency is justified by the task.
- Keep secrets out of the repository. Use committed example configuration files
  for documented settings and local ignored environment files for credentials.
- Refer to `.pre-commit-config.yaml`, `.github/workflows/`, and project manifests
  for the current automation and tool configuration.

## Change and review workflow

- Start from the smallest change that solves the requested problem; make
  architectural refactors separately reviewable when possible.
- Preserve backward compatibility for public API, configuration, and evaluation
  contracts unless the task explicitly authorizes a breaking change. Document
  migration steps when breaking changes are necessary.
- Before committing, inspect the staged diff for unintended files, generated
  artifacts, and secrets. Do not commit or push unless explicitly requested.
- Pull requests should explain behavior changes, validation performed, and any
  configuration, deployment, or migration implications.

## Key references

| Topic | Location |
| --- | --- |
| Project overview and commands | `README.md`, `make help` |
| Developer setup | `docs/dev/setup.md` |
| Architecture | `docs/dev/architecture.md` |
| Evaluation contract | `docs/dev/evaluation.md` |
| Observability | `docs/dev/observability.md` |
| Python tooling | `pyproject.toml`, `backend/pyproject.toml` |
| Frontend tooling | `frontend/package.json` |
| Automation | `.pre-commit-config.yaml`, `.github/workflows/` |
