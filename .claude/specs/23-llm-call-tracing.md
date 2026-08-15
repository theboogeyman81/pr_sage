# Feature 23: LLM Call Tracing

## Goal
Every Gemini API call emits one structured log line with prompt-hash, token
counts, cost estimate, and duration, so calls are auditable and totals are
aggregatable via `jq` without a persistent trace store.

## In scope
- `app/llm/cost_table.py` — static `COST_PER_TOKEN` dict keyed by model string;
  `estimate_cost(model, input_tokens, output_tokens) -> float | None` (returns
  `None` for unknown models instead of raising)
- Tracing logic added inside `GeminiClient._call` in `app/llm/gemini_client.py`:
  - Measures wall-clock duration with `time.perf_counter()` (start before the
    SDK call, stop after; does **not** include tenacity retry wait time —
    each attempt is timed independently)
  - Computes `prompt_hash`: first 16 hex chars of SHA-256 of the serialised
    `messages` list (JSON-encoded, UTF-8); logs the hash, never the content
  - On success emits one `structlog` log at INFO level with fields:
    `event="llm_call"`, `model`, `prompt_hash`, `input_tokens`,
    `output_tokens`, `cost_usd` (float rounded to 6 dp, or `None`),
    `duration_ms` (int, wall ms for this attempt)
  - On LLM exception the same fields are logged at WARNING level with an
    additional `error=str(exc)` field before re-raising
- Tests in `tests/test_llm_tracing.py`

## Out of scope
- Persistent trace database or file sink
- Aggregated per-review totals (these can be derived by `jq`-grouping on
  `correlation_id` from the F22 structlog context)
- Streaming or multimodal Gemini calls
- Per-repo or dynamic cost overrides

## File structure
```
app/llm/
    cost_table.py          ← new
    gemini_client.py       ← modified (add tracing in _call)
tests/
    test_llm_tracing.py    ← new
```

## Contracts

### `app/llm/cost_table.py`
```python
# USD per 1 token (not per 1M)
COST_PER_TOKEN: dict[str, dict[str, float]] = {
    "gemini-2.0-flash": {
        "input":  0.10 / 1_000_000,
        "output": 0.40 / 1_000_000,
    },
    "gemini-1.5-flash": {
        "input":  0.075 / 1_000_000,
        "output": 0.30  / 1_000_000,
    },
    "gemini-1.5-pro": {
        "input":  1.25 / 1_000_000,
        "output": 5.00 / 1_000_000,
    },
}

def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float | None:
    ...
```

### Trace log shape (emitted by `GeminiClient._call`)
```json
{
  "event": "llm_call",
  "model": "gemini-2.0-flash",
  "prompt_hash": "a3f9c1d2e4b7...",
  "input_tokens": 512,
  "output_tokens": 128,
  "cost_usd": 0.000103,
  "duration_ms": 842,
  "level": "info",
  "timestamp": "2026-08-07T10:00:00Z",
  "request_id": "..."
}
```
`request_id` / `correlation_id` come automatically from the F22 structlog
contextvars — no extra plumbing needed.

## Dependencies
No new packages. Uses `hashlib`, `json`, `time` (all stdlib) and `structlog`
(already pinned at `25.4.0`).

## Tests
- `test_trace_log_on_success`: mock `_client.models.generate_content`, call
  `GeminiClient.complete`, capture structlog output, assert log contains
  `event="llm_call"`, `model`, `prompt_hash` (16-char hex string),
  `input_tokens`, `output_tokens`, `cost_usd` (float), `duration_ms` (int ≥ 0)
- `test_trace_log_on_error`: mock raises `LLMServerError`, assert WARNING log
  emitted with `error` field, original exception still propagates
- `test_estimate_cost_known_model`: known model + token counts → correct float
- `test_estimate_cost_unknown_model`: unknown model string → returns `None`
- `test_prompt_hash_is_deterministic`: same messages → same hash every call
- `test_prompt_hash_changes_with_input`: different messages → different hash

## Acceptance criteria
1. Every call to `GeminiClient.complete` emits exactly one structured log line
   at INFO (success) or WARNING (error) with all six required fields
2. `cost_usd` is `None` for model strings not in `COST_PER_TOKEN`
3. `prompt_hash` is a 16-character lowercase hex string derived from message
   content — no raw prompt text ever appears in logs
4. `duration_ms` reflects only the single SDK call, not tenacity retry delays
5. Running `pytest tests/test_llm_tracing.py -v` → 6 tests pass
6. `pytest tests/ -v` → all existing tests continue to pass
7. On a real review run, `jq 'select(.event=="llm_call") | {model,cost_usd,tokens:.input_tokens+.output_tokens}'`
   on the log output returns one object per LLM call
