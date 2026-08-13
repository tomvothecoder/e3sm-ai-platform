Build a minimal but extensible **E3SM AI Platform** prototype focused initially on **E3SM-ASSIST**.

## Repository

Create a new repo named `e3sm-ai-platform` with:

- Python 3.13 + `uv`
- FastAPI backend
- React + TypeScript + Vite frontend
- pytest, Ruff, type checking
- frontend lint/typecheck/build
- GitHub Actions
- clear `backend/` and `frontend/` separation

## Prototype

Build an end-to-end E3SM-ASSIST chat prototype using:

- curated RAG for stable authoritative E3SM documentation
- web search fallback for current information or corpus gaps
- interfaces for future SimBoard/GitHub/API/MCP sources
- explicit insufficient-evidence behavior

Keep retrieval, routing, generation, and integrations independently testable and provider-independent.

## Corpus

Index a small representative set of official E3SM material from:

- E3SM User Guide
- Running E3SM Guide
- EAM/EAMxx
- ELM
- E3SM Diagnostics
- E3SM-Unified

Target roughly 20-50 useful pages/sections.

Preserve source URL, section, component/topic, version, authority, and provenance for citations.

## Backend

Implement:

- `POST /query`
- ingestion + chunking
- embedding/vector retrieval abstractions
- citations
- structured routing between:
  - curated RAG
  - web search
  - future operational/tool source
  - insufficient evidence

- route and retrieved evidence in the response for debugging/evaluation

## Frontend

Build a minimal chat UI with:

- question input
- answer display
- citations
- loading/error states
- expandable evidence
- debug view showing selected route and retrieved sources

Do not add authentication, persistent history, or elaborate UI infrastructure.

## Evaluation

Create about 20 representative E3SM questions and evaluate:

- routing correctness
- retrieval relevance
- citation/provenance presence
- insufficient-evidence behavior

Prefer deterministic tests without live LLM/web calls where practical.

## Architecture

Favor a small working vertical slice over a framework.

Preserve extension points for:

- pgvector
- hybrid retrieval/reranking
- SimBoard APIs
- GitHub MCP
- Rovo/Atlassian
- tool-calling agents
- conversational context
- additional E3SM applications

Use the configured multi-agent workflow selectively. Parallelize frontend, backend, ingestion, and evaluation work when ownership is clearly separated.

## Verification

Run backend tests, lint, and type checks.

Run frontend tests, lint, type checks, and production build.

Document setup, architecture, ingestion, routing, evaluation, limitations, and next steps in `README.md`.

At completion summarize architecture, agents/models used, evaluation results, reviewer findings, verification results, and recommended next steps.
