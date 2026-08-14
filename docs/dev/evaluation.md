# Evaluation guide

The `evaluation/` package is an independent deterministic pytest suite for the
E3SM-ASSIST response contract. It does not import a backend by default. Instead,
pytest loads an adapter named by `E3SM_ASSIST_EVALUATOR` once per session and
calls it for each fixture question.

## Running evaluation

Run the evaluation against the packaged backend adapter from the repository root:

```bash
E3SM_ASSIST_EVALUATOR=e3sm_assist.evaluation_adapter:evaluate \
  uv run --all-packages pytest evaluation
```

The equivalent Make target is:

```bash
make evaluation-test
```

`--all-packages` is required so the evaluation and backend workspace packages are
available together. If `E3SM_ASSIST_EVALUATOR` is not set, the tests skip rather
than guessing a backend package path.

## Adapter contract

The adapter must be a synchronous callable with this shape:

```python
evaluate(question: str) -> Mapping[str, object]
```

It receives one question and returns a mapping with this response schema:

```python
{
    "answer": "...",                         # str
    "route": "curated",                       # curated | web | future_operational | insufficient_evidence
    "retrieved_evidence": [
        {"source_id": "user-guide:compsets", "text": "..."}
    ],                                        # flat list, not nested by source
    "citations": [
        {"source_id": "user-guide:compsets", "provenance": "official URL or corpus provenance"}
    ],
    "insufficient_evidence": False,           # bool
}
```

Critical details:

- `route` must be exactly one of `curated`, `web`, `future_operational`, or
  `insufficient_evidence`.
- `retrieved_evidence` must be a flat list of records with `source_id`.
- Each citation must include both `source_id` and `provenance`.
- `insufficient_evidence` must be a boolean.
- Unsupported cases must return the `insufficient_evidence` route, set
  `insufficient_evidence` to `true`, return no retrieved evidence, and say that
  evidence is insufficient in the answer.

An API adapter may call `POST /query` and normalize its response to this mapping.
Keep HTTP/client details inside the adapter rather than in the tests.

## Fixture expectations

Fixtures live in `evaluation/fixtures/e3sm_questions.json`. Curated corpus
records must use the fixture `source_id` values, or the adapter must translate
backend identifiers to them. For curated cases, expected source IDs must appear
in `retrieved_evidence`, and citations must carry provenance.

The current tests check route and retrieval contract behavior, citation
provenance for curated answers, and explicit insufficient-evidence behavior.
They are designed to run without live LLM or web requests.

## Backend packaged adapter

The backend ships `e3sm_assist.evaluation_adapter:evaluate`. It initializes the
application service once per process, sends each fixture question through the
same query service, and returns only the stable evaluation mapping fields.

## Validation

Useful evaluation-specific commands are:

```bash
make evaluation-test
make evaluation-lint
make evaluation-typecheck
```

For repository-level Ruff, ty, and mypy guidance, see [setup.md](setup.md).
