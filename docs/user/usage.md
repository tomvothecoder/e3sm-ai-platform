# E3SM-ASSIST usage guide

E3SM-ASSIST is a local prototype assistant for questions supported by a curated
E3SM documentation corpus. It answers from accepted curated evidence when
available, otherwise it returns an explicit insufficient-evidence response for
current web, live operational/tool, or unsupported requests.

## Start the backend

From the repository root:

```bash
uv sync --all-packages --all-groups
uv run --all-packages --directory backend uvicorn e3sm_assist.app:app --reload
```

The backend starts the FastAPI application `e3sm_assist.app:app`. Useful local
endpoints are:

- `GET http://localhost:8000/health`
- `POST http://localhost:8000/query`

Example direct query:

```bash
curl -s http://localhost:8000/query \
  -H 'Content-Type: application/json' \
  -d '{"question":"How do I use E3SM-Unified?"}'
```

## Start the frontend

In another terminal from the repository root:

```bash
npm --prefix frontend ci
npm --prefix frontend run dev
```

The Vite development server proxies relative `/query` calls to
`VITE_DEV_API_PROXY_TARGET`, defaulting to `http://localhost:8000`. Leave
`VITE_API_BASE_URL` empty for the local proxy. Set `VITE_API_BASE_URL` only when
the frontend must call a full backend URL directly; the backend CORS setting must
allow that origin.

## Query behavior

`POST /query` accepts:

```json
{
  "question": "How do I create an E3SM case?",
  "top_k": 4,
  "include_evidence": true
}
```

The response includes an answer, route, route alias, citations, evidence fields,
an `insufficient_evidence` flag, and debug metadata. Current route values are:

- `curated`: accepted curated documentation evidence supports the answer.
- `web`: the question appears to require current web information; no live web
  provider is configured in this prototype.
- `future_operational`: the question appears to require live operational,
  GitHub, SimBoard, scheduler, or tool data; only provider-independent
  interfaces exist today.
- `insufficient_evidence`: the curated corpus does not provide enough support or
  the request is unsupported.

Curated answers include citation provenance and avoid adding claims beyond the
accepted evidence. Non-curated routes return no accepted evidence or citations.

## Optional LivAI generation

Deterministic generation is the default. To opt into LivAI for answers that
already have curated supporting evidence, configure the backend process only:

```bash
ASSISTANT_GENERATOR=livai
ASSISTANT_LIVAI_API_KEY=your-secret-key
ASSISTANT_LIVAI_MODEL=gpt-5.5
ASSISTANT_LIVAI_BASE_URL=https://livai-api.llnl.gov/
```

Inject secrets through an untracked backend environment, `backend/.env`, or a
deployment secret manager. Do not use `VITE_` names for backend secrets and never
commit API keys. LivAI provider errors fall back to deterministic,
evidence-constrained output and do not enable live web retrieval.

## Observability

The backend returns an `X-Request-ID` header and emits bounded request-completion
logs. For local OpenTelemetry Collector and Jaeger setup, see the canonical
[observability guide](../dev/observability.md).
