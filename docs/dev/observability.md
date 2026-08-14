# Observability guide

This guide describes observability expectations for the current E3SM-ASSIST
prototype and separates the implemented baseline from deployment and governance
work that must be completed before production use. The implementation status in
[`prototype-status.md`](prototype-status.md) remains the source of truth for
delivered features; this document focuses on durable operating guidance.

## Implemented baseline

- The browser sends chat requests to the FastAPI backend `POST /query` endpoint.
  Local development can use the Vite `/query` proxy described in the
  [README](../../README.md).
- The backend service performs deterministic retrieval, accepted-evidence
  filtering, route selection, and deterministic generation. Optional LivAI
  generation is available only when backend-only LivAI environment variables are
  configured.
- Query responses expose `route`, `route_alias`, citations, returned evidence,
  `retrieved_evidence`, and debug metadata for evaluation and support.
- The service has a `GET /health` endpoint with corpus summary information.
- The backend includes privacy-preserving observability hooks: OpenTelemetry
  FastAPI instrumentation, internal spans around query/retrieval/acceptance/
  routing/generation, JSON request-completion logs with an allow-listed field
  set, and a server-generated `X-Request-ID` response header.
- The frontend sends a W3C `traceparent` header for `/query` requests and can
  display the returned `X-Request-ID` in generic error messages.
- OTLP trace export is disabled unless the backend is explicitly configured with
  an OTLP HTTP traces endpoint.

Telemetry `service.name` identifies each emitting process: the backend API uses
`e3sm-assist-api`, a future browser frontend uses `e3sm-assist-web`, and
`e3sm-assist` remains the shared product label.

Not currently implemented:

- A production or shared OpenTelemetry Collector deployment, sidecar, service,
  Helm chart, or managed telemetry backend. The repository has only a local
  Docker development stack for trace inspection.
- Metrics export or log export through OpenTelemetry.
- Caller-supplied request ID validation and propagation.
- Query-specific structured logs for route, evidence counts, provider fallback,
  corpus snapshots, or policy versions.
- Authentication, authorization, audit logging, persistent conversation history,
  or write-capable tools.

## Local Docker Collector and Jaeger

The local development trace stack is defined in
[`deploy/observability/docker-compose.yml`](../../deploy/observability/docker-compose.yml).
It is intended for developer-only inspection of trace metadata.

Prerequisite: Docker Desktop must be installed and running.

Start the local Collector and Jaeger stack from the repository root:

```bash
make observability-up
```

Configure the backend process to export traces to the local Collector. The OTLP
endpoint must be exactly:

```bash
E3SM_ASSIST_OTLP_ENDPOINT=http://localhost:4318/v1/traces
```

Optional local resource labels:

```bash
E3SM_ASSIST_SERVICE_NAME=e3sm-assist-api
E3SM_ASSIST_DEPLOYMENT_ENVIRONMENT=local
```

Start the backend with those variables in the backend process environment:

```bash
E3SM_ASSIST_OTLP_ENDPOINT=http://localhost:4318/v1/traces \
E3SM_ASSIST_SERVICE_NAME=e3sm-assist-api \
E3SM_ASSIST_DEPLOYMENT_ENVIRONMENT=local \
uv run --all-packages --directory backend uvicorn e3sm_assist.app:app --reload
```

Submit a query from the frontend or directly:

```bash
curl -s http://localhost:8000/query \
  -H 'Content-Type: application/json' \
  -d '{"question":"How do I use E3SM-Unified?"}'
```

Open Jaeger at <http://localhost:16686> and search for the configured service
name. Helpful local targets:

```bash
make observability-status
make observability-logs
make observability-down
```

The compose stack binds exposed ports to loopback only (`127.0.0.1`). Do not
expose the Collector or Jaeger UI on shared networks. The stack is still subject
to the prohibited-payload rules in this guide: retain trace metadata only, not
raw questions, answers, prompts, evidence text, provider payloads, or secrets.
The Collector removes `net.peer.ip` and `http.user_agent` before batch processing
and local Jaeger export; production Collectors must maintain an equivalent policy.

`make observability-down` runs Docker Compose `down` without a volume-deletion
flag, so it stops containers without explicitly deleting Docker volumes. The
current Jaeger development stack does not define persistent storage, so local
trace data should be treated as ephemeral.

Troubleshooting:

- Docker daemon unavailable: start Docker Desktop, wait until the engine is
  running, then rerun `make observability-up`.
- Port `4318` already in use: stop the other local OTLP HTTP Collector or change
  the compose port mapping and update `E3SM_ASSIST_OTLP_ENDPOINT` consistently.
- Port `16686` already in use: stop the other Jaeger instance or change the
  Jaeger UI port mapping before opening the UI.
- Port `13133` already in use: stop the other local Collector health endpoint or
  change the compose health-check port mapping.
- No traces in Jaeger: confirm the backend was started after setting
  `E3SM_ASSIST_OTLP_ENDPOINT=http://localhost:4318/v1/traces`, submit a new
  query, then search for the configured service name.

## Trace topology

The current frontend creates a W3C trace context and the backend instruments
FastAPI plus internal query spans. Use one trace per user-visible query. The
intended durable topology is:

1. `frontend.chat_submit`: UI event, input validation, and client request timing.
2. `http.post_query`: backend `POST /query` request handling.
3. `retrieval.search`: vector or lexical search over the curated corpus.
4. `retrieval.acceptance`: accepted-evidence filtering that separates supported
   evidence from unverified raw candidates.
5. `routing.select`: deterministic route decision with the route value and
   sanitized reason.
6. `generation.build`: evidence-constrained deterministic response construction.
7. `generation.provider`: optional provider call, currently LivAI only when
   explicitly enabled for curated-evidence answers.

Current backend span names are implementation-oriented (`assist.query`,
`rag.retrieve`, `rag.accept`, `assist.route`, and `generation.generate`). Treat
the topology above as the long-term naming/coverage goal, especially for adding
separate frontend and provider spans.

Recommended low-cardinality span attributes:

- `app.name`: `e3sm-assist`
- `http.route`: `/query`
- `rag.route`: one of `curated`, `web`, `future_operational`, or
  `insufficient_evidence`
- `rag.route_alias`: response alias such as `curated_rag`
- `rag.top_k`: requested retrieval count
- `rag.include_evidence`: boolean request setting
- `rag.accepted_evidence_count`: number of accepted chunks used for curated
  generation
- `rag.candidate_count`: number of retrieved candidates considered
- `rag.corpus_snapshot_id`: stable corpus snapshot identifier when available
- `rag.retrieval_policy_version`: retrieval/chunking/scoring policy version when
  available
- `llm.provider`: `deterministic` or `livai`
- `llm.model`: configured model name when a hosted provider is used
- `error.type`: sanitized exception class or internal error code

Do not attach full questions, answers, source text, prompts, API keys, cookies,
authorization headers, IP addresses, or user identifiers as span attributes.

## Data classification and prohibited payloads

Treat observability data as operational metadata, not as a second copy of chat
content.

Allowed in logs/traces by default:

- Request method, route template, status code, latency, and coarse response size.
- Selected route, route alias, accepted evidence count, candidate count, `top_k`,
  and `include_evidence`.
- Public source identifiers, corpus version labels already present in source
  metadata, and policy/snapshot identifiers.
- Sanitized provider state such as `livai_used`, `livai_fallback`, and sanitized
  LivAI error codes.

Prohibited unless a separate data-governance review explicitly approves it:

- Raw user questions, generated answers, prompt bodies, retrieved chunk text, or
  full evidence snippets.
- API keys, bearer tokens, cookies, session IDs, private repository URLs, and
  deployment secrets.
- Protected operational data from SimBoard, GitHub, HPC schedulers, allocations,
  workflows, or user-specific cases.
- Personal data, network identifiers that can identify a person or workstation,
  or persistent user identifiers.
- Provider request/response payloads and stack traces that may contain payload
  fragments.

For debugging, prefer a short-lived local reproduction with fixtures or a redacted
payload supplied through the support playbook below rather than increasing log
payload detail in shared environments.

## Structured log schema

The backend currently emits bounded JSON request-completion logs through the
application logger. The implemented event is `http.request.complete`, with only
allow-listed request metadata such as method, route, status, duration, outcome,
request ID, and active trace/span IDs when available. It does not log request
bodies, questions, answers, prompts, evidence text, provider payloads, or
arbitrary exception details.

When query-specific logs are added, emit one JSON object per event and keep
fields stable. Suggested future event names:

- `query.received`
- `retrieval.completed`
- `evidence.accepted`
- `routing.selected`
- `generation.completed`
- `provider.fallback`
- `query.completed`
- `query.failed`

Recommended fields:

| Field | Description |
| --- | --- |
| `timestamp` | RFC 3339 UTC timestamp. |
| `level` | `INFO`, `WARN`, or `ERROR`. |
| `event` | Stable event name. |
| `service` | Emitting process name, such as `e3sm-assist-api` or future `e3sm-assist-web`. |
| `environment` | Deployment environment label. |
| `request_id` | Propagated request ID once implemented. |
| `trace_id` | OpenTelemetry trace ID once implemented. |
| `span_id` | OpenTelemetry span ID once implemented. |
| `http_method` | HTTP method, for example `POST`. |
| `http_route` | Route template, for example `/query`. |
| `http_status` | Response status code. |
| `duration_ms` | Event or request duration. |
| `route` | Query route value. |
| `route_alias` | Query route alias. |
| `routing_reason_code` | Stable sanitized reason code; avoid free-text payloads. |
| `top_k` | Requested retrieval count. |
| `include_evidence` | Boolean request setting. |
| `candidate_count` | Retrieved candidate count. |
| `accepted_evidence_count` | Accepted evidence count. |
| `citation_count` | Citation count returned to the client. |
| `corpus_snapshot_id` | Corpus snapshot identifier when available. |
| `retrieval_policy_version` | Retrieval/chunking/scoring policy version. |
| `prompt_policy_version` | Prompt and generation policy version. |
| `provider` | `deterministic`, `livai`, or another future provider. |
| `provider_model` | Hosted provider model name when applicable. |
| `provider_fallback` | Boolean fallback indicator. |
| `error_code` | Sanitized internal error code. |

Example shape, with placeholder IDs only:

```json
{
  "timestamp": "2026-08-13T00:00:00Z",
  "level": "INFO",
  "event": "query.completed",
  "service": "e3sm-assist-api",
  "environment": "local",
  "request_id": "not-implemented",
  "trace_id": "not-implemented",
  "http_method": "POST",
  "http_route": "/query",
  "http_status": 200,
  "duration_ms": 42,
  "route": "curated",
  "route_alias": "curated_rag",
  "top_k": 4,
  "include_evidence": true,
  "candidate_count": 8,
  "accepted_evidence_count": 4,
  "citation_count": 3,
  "corpus_snapshot_id": "curated-corpus:pending-version",
  "retrieval_policy_version": "pending-version",
  "prompt_policy_version": "deterministic-v1",
  "provider": "deterministic",
  "provider_fallback": false
}
```

## OTLP Collector deployment and environment configuration

The repository-owned Collector configuration is local-development only. There is
no production or shared Collector deployment in this repository; do not operate
or depend on one as if it exists.

For local development, point the backend at the local Docker Collector with
backend-only environment variables:

```bash
E3SM_ASSIST_OTLP_ENDPOINT=http://localhost:4318/v1/traces
E3SM_ASSIST_SERVICE_NAME=e3sm-assist-api
E3SM_ASSIST_DEPLOYMENT_ENVIRONMENT=local
E3SM_ASSIST_OTLP_HEADERS=
```

`E3SM_ASSIST_OTLP_ENDPOINT` must remain unset to disable export. Outside local
development, set it only for an approved Collector or telemetry gateway.
Optional `E3SM_ASSIST_OTLP_HEADERS` uses comma-separated `key=value` entries for
exporter headers and must not be logged or exposed to the frontend.

Before enabling OTLP export, add an explicit deployment design that covers:

- Collector ownership, deployment mode, network path, TLS, authentication, and
  egress approval.
- Which signals are enabled first: traces, metrics, logs, or a limited subset.
- Redaction and attribute allow-listing at the application and collector layers.
- Sampling strategy and per-environment export controls.
- Operational runbooks for collector outages, backpressure, and dropped telemetry.

Future deployments may prefer standard OpenTelemetry environment variables where
possible, for example:

```bash
OTEL_SERVICE_NAME=e3sm-assist-api
OTEL_RESOURCE_ATTRIBUTES=deployment.environment=local,app.name=e3sm-assist
OTEL_EXPORTER_OTLP_ENDPOINT=https://collector.example.invalid:4318
OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
OTEL_TRACES_SAMPLER=parentbased_traceidratio
OTEL_TRACES_SAMPLER_ARG=0.10
```

These `OTEL_*` variables are future deployment examples, not current repository
requirements. Keep provider secrets such as `ASSISTANT_LIVAI_API_KEY` out of all
telemetry configuration and exported resource attributes.

## Sampling and retention

Current local development has no repository-owned telemetry retention policy.
Traces are not exported unless `E3SM_ASSIST_OTLP_ENDPOINT` is set. The local
Jaeger stack is for short-lived debugging, not durable retention.

Recommended future defaults:

- Local development: tracing disabled by default; allow opt-in console or local
  collector export for short debugging sessions.
- Shared non-production: low-rate head sampling such as 5-10% for successful
  requests, with 100% sampling for errors and provider fallbacks when payload
  redaction is enforced.
- Production: start conservatively, for example 1-5% successful request traces
  and 100% sanitized errors, then adjust from measured volume and support needs.
- Retention: keep high-cardinality trace data short-lived, such as 7-30 days;
  keep aggregate metrics longer according to deployment policy.
- Never increase sampling by logging raw payloads. Increase metadata sampling or
  reproduce with fixtures instead.

## Request ID support playbook

The backend currently generates a new opaque request ID for each HTTP request and
returns it as `X-Request-ID`; the frontend displays that value for failed
requests when available. Caller-supplied request IDs are not accepted or
propagated.

Support requests should include only safe correlation details:

1. Approximate UTC timestamp and environment.
2. Frontend URL and backend deployment target, if known.
3. HTTP status code and visible error message.
4. Returned route, route alias, citation count, and whether insufficient evidence
   was returned.
5. A redacted or paraphrased question if the original may contain sensitive
   operational or personal data.
6. Whether optional LivAI generation was enabled in the backend environment.

Future request ID requirements:

- Accept a caller-supplied `X-Request-ID` only after validating length and
  allowed characters; otherwise generate a new opaque ID.
- Return the selected ID in every response header.
- Include the ID in frontend error displays, backend structured logs, traces, and
  provider fallback metadata.
- Expose `X-Request-ID` with CORS `expose_headers` so browser clients can read
  response correlation IDs; keep request headers such as `traceparent` and
  `tracestate` in the separate CORS `allow_headers` list.
- Never encode user IDs, questions, source text, or secrets in the request ID.

## Audit roadmap before auth or write-capable tools

The prototype has no authentication and no write-capable tool integrations.
Before enabling authenticated access, SimBoard/GitHub/MCP adapters, scheduler
actions, or any other write path, define a separate audit roadmap. It must be
approved before implementation and cover:

- Identity source, authentication flow, session lifetime, and service-account
  handling.
- Authorization model for each tool action and each data source.
- Immutable audit event schema separate from general operational logs.
- Audit event integrity, retention, legal hold, access review, and break-glass
  procedures.
- Tool input/output provenance, including whether a result came from curated docs,
  live web, GitHub, SimBoard, an HPC scheduler, or another adapter.
- Human confirmation requirements for write operations.
- Redaction and access controls for protected operational data.
- Regression tests and dry-run mode for every write-capable adapter.

General observability logs are not a substitute for audit logs.

## RAG reproducibility snapshots and policy versions

Current reproducibility baseline:

- The bundled curated corpus is static JSON loaded by the backend.
- Each source record preserves URL, section, component, version, authority, and
  provenance.
- Chunk IDs are deterministic for a given corpus entry and chunking policy.
- Evaluation fixtures use deterministic retrieval, routing, citation, and
  insufficient-evidence checks.

Current gaps:

- No explicit corpus snapshot identifier is exposed by the API.
- No retrieval, acceptance, routing, prompt, or generation policy version is
  emitted in responses, logs, or traces.
- No automated corpus freshness or source-diff report is published.

Future policy:

- Assign a stable `corpus_snapshot_id` to every reviewed corpus build.
- Version the chunking, embedding, scoring, acceptance, routing, and prompt
  policies independently.
- Record the snapshot and policy versions in evaluation artifacts, structured
  logs, and trace attributes.
- Preserve enough metadata to reproduce the selected route and citations from a
  historical question without storing prohibited payloads in observability data.
- Require review when corpus snapshots or policy versions change, especially when
  citation behavior or insufficient-evidence behavior changes.
