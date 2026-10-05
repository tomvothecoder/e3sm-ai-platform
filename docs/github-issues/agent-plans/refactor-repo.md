# E3SM Compass Platform Refactor Plan

## Goal

Clarify the product boundary and make the backend easier to evolve during rapid
prototyping:

- The chat assistant is **E3SM Compass**.
- The repository and backend are the **E3SM AI Platform**.
- The backend Python package is `e3sm_ai_platform`.

This is a structural and naming refactor. It preserves lexical, semantic, and
hybrid retrieval; the optional LivAI generator; and observability support.

## Naming policy

- Use **E3SM AI Platform** for backend packages, distribution metadata,
  operational configuration, logging, tracing, and deployment identifiers.
- Use **E3SM Compass** for the assistant-facing UI, API title, prompt text,
  evaluation contract, and user-facing documentation.
- Replace repository-controlled `e3sm_assist`, `e3sm-assist`, and
  `E3SM_ASSIST_*` identifiers without compatibility aliases. Historical
  records may retain them only when explicitly allowlisted in the final stale
  name audit.

## Target backend layout

```text
backend/src/e3sm_ai_platform/
├── api/
│   └── app.py
├── application/
│   ├── generation.py
│   ├── routing.py
│   └── service.py
├── domain/
│   └── models.py
├── infrastructure/
│   ├── observability.py
│   └── settings.py
├── integrations/
│   └── livai.py
├── knowledge/
│   ├── corpus.py
│   ├── curation.py
│   ├── data/
│   │   └── curated_corpus.json
│   ├── interfaces.py
│   └── retrieval.py
└── evaluation.py
```

The corpus is packaged data. Load its default copy with `importlib.resources`,
not a source-tree-relative `Path`, while retaining an explicit filesystem-path
override for tests and curation tools.

## Implementation phases

Each phase is a separately reviewable commit. A phase is committed only after
its stated checks pass.

### Phase 1: Establish the platform package scaffold

- Add `e3sm_ai_platform` and its architectural subpackages.
- Move domain models, knowledge/corpus code, application code, integration
  code, and infrastructure code into their target modules.
- Extract `CompassService` into `application/service.py`; leave HTTP wiring in
  `api/app.py`.
- Move the evaluator to `evaluation.py`. It must instantiate the application
  service directly, without importing FastAPI HTTP wiring or configuring
  observability as an import side effect.
- Load the curated corpus as package data with `importlib.resources`.
- Preserve lexical, semantic, and hybrid retrieval plus LivAI and observability
  behavior.

**Commit:** `refactor(backend): scaffold e3sm platform package`

**Checks:** focused backend import, retrieval, LivAI, observability, evaluator
isolation, and packaged-corpus resource tests.

### Phase 2: Complete the backend package rename

- Rename all backend-internal imports and backend tests from `e3sm_assist` to
  `e3sm_ai_platform`.
- Remove the old package with no compatibility alias.
- Rename the distribution to `e3sm-ai-platform-backend` and update Hatch,
  Ruff, and ty configuration; remove obsolete mypy dependency, configuration,
  and Makefile targets because ty is authoritative.
- Update scripts and startup configuration to
  `e3sm_ai_platform.api.app:app`.
- Replace backend operational configuration from `E3SM_ASSIST_*` and generic
  `ASSISTANT_*` names with clear, unprefixed variables, with no compatibility
  variables.
- Rename backend observability and deployment identifiers, including the
  default OpenTelemetry service name, logger name, trace attributes, and the
  observability Compose project name, to E3SM AI Platform terminology.

**Commit:** `refactor(backend): rename assist package to platform`

**Checks:** backend test suite, Ruff, ty, a direct Uvicorn application import,
and a search confirming no backend-controlled old package or operational names
remain.

### Phase 3: Rewire evaluation and repository automation

- Move evaluation wiring to `e3sm_ai_platform.evaluation:evaluate`.
- Rename `E3SM_ASSIST_EVALUATOR` to `E3SM_COMPASS_EVALUATOR` in evaluation
  fixtures, Makefile targets, CI, and documentation.
- Rename evaluation distribution metadata and test/module names from
  `e3sm-assist`/`e3sm_assist` to E3SM Compass terminology.
- Update all repository-controlled callers without a compatibility variable.

**Commit:** `refactor(evaluation): use compass evaluator contract`

**Checks:** standalone evaluation suite using `E3SM_COMPASS_EVALUATOR`, the
affected Makefile command, and an evaluator import that verifies FastAPI app
construction and observability setup are not required.

### Phase 4: Rebrand the assistant-facing experience

- Rename assistant-facing labels, API title, frontend text, tests, README, and
  user/developer documentation from E3SM-ASSIST to E3SM Compass.
- Retain E3SM AI Platform for backend and repository references.
- Rename the frontend package metadata to `e3sm-compass-frontend`.
- Update the LivAI system prompt to identify the assistant as E3SM Compass.

**Commit:** `refactor(branding): rename assistant to e3sm compass`

**Checks:** frontend tests, lint, type check, production build, and a search
for stale assistant-facing labels.

### Phase 5: Clean generated artifacts and verify integration

- Add `backend/.data/` to `.gitignore` and remove generated local retrieval
  artifacts from the working tree if present. Do not claim a deletion when no
  such artifacts are tracked; assert instead that generated artifacts remain
  untracked.
- Build the backend wheel, install it into a clean environment, then import
  `e3sm_ai_platform.api.app:app` and load the packaged corpus.
- Run final integration checks and inspect for stale module paths, evaluator
  names, startup targets, operational identifiers, and branding. Search all
  tracked files; allow historical references only in an explicit, documented
  allowlist rather than rewriting archived records.
- Request an independent review of the completed refactor, address valid
  findings, and rerun impacted checks.

**Commit:** `chore: ignore generated retrieval artifacts`

**Checks:**

```bash
uv run --all-packages ruff format backend evaluation
uv run --all-packages ruff check backend evaluation
uv run --all-packages ty check
uv run --all-packages pre-commit run --all-files
uv run --all-packages pytest backend/tests
E3SM_COMPASS_EVALUATOR=e3sm_ai_platform.evaluation:evaluate \
  uv run --all-packages pytest evaluation
make frontend-test frontend-lint frontend-typecheck frontend-build
```

Also run the wheel-install smoke test and retain its command/output in the
commit or review notes.

## Acceptance criteria

- `e3sm_assist` no longer exists as a source package or repository-controlled
  import path, filename, distribution name, or operational identifier, except
  for the documented historical allowlist.
- API startup works with `e3sm_ai_platform.api.app:app`.
- Evaluation works with
  `E3SM_COMPASS_EVALUATOR=e3sm_ai_platform.evaluation:evaluate`.
- The evaluator imports and runs without importing HTTP wiring or requiring
  FastAPI observability setup.
- The built backend wheel installs cleanly and loads its curated corpus outside
  the source tree.
- Lexical, semantic, and hybrid retrieval tests retain their existing behavior.
- LivAI and observability tests retain their existing behavior.
- User-facing assistant text, prompt text, evaluation contract, and frontend
  package metadata identify the product as E3SM Compass.
- Backend configuration, logging, tracing, deployment identifiers, and backend
  package metadata identify the product as E3SM AI Platform.
