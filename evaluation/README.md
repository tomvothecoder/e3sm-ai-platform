# E3SM-ASSIST evaluation

This directory is an independent, deterministic integration evaluation. It does not import a backend by default, so it remains usable while the backend is being developed.

## Adapter contract

Provide either a small synchronous Python adapter or an API adapter that implements the same callable contract. Configure the Python adapter before running pytest:

```sh
E3SM_ASSIST_EVALUATOR=e3sm_assist.evaluation_adapter:evaluate \
  uv run --all-packages pytest evaluation
```

Run this command from the repository root. `--all-packages` installs the
evaluation and backend workspace packages; the environment variable names the
backend's evaluation adapter.

`evaluate(question: str) -> Mapping[str, object]` receives one question and must return a mapping with this shape:

```python
{
    "answer": "...",                         # str
    "route": "curated",                       # exactly: curated | web | future_operational | insufficient_evidence
    "retrieved_evidence": [
        {"source_id": "user-guide:compsets", "text": "..."}  # flat list, not nested by source
    ],
    "citations": [
        {"source_id": "user-guide:compsets", "provenance": "official URL or corpus provenance"}
    ],
    "insufficient_evidence": False,
}
```

`retrieved_evidence` is always a flat list of records with `source_id`. Each citation has both `source_id` and `provenance`. `insufficient_evidence` is a boolean. An API adapter may call `POST /query` and normalize its response to this mapping; keep HTTP/client details out of the tests.

The adapter may initialize the application/service internally. Pytest imports it once per session and invokes it once for every fixture question. Keep it deterministic: no live LLM or web requests are needed for these assertions.

Curated corpus records must use the `source_id` values named in `fixtures/e3sm_questions.json` (or the adapter must translate backend identifiers to them). For curated cases, expected source IDs must appear in `retrieved_evidence`; citations must contain both `source_id` and `provenance`. Unsupported cases must return the `insufficient_evidence` route, set `insufficient_evidence` to `true`, return no retrieved evidence, and say that evidence is insufficient in the answer.

Without `E3SM_ASSIST_EVALUATOR`, tests are skipped intentionally rather than guessing backend package paths.
