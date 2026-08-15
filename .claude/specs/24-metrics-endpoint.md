# Feature 24: Metrics Endpoint

## Goal
Expose a `/metrics` endpoint in Prometheus text format so counters and
histograms for reviews, LLM calls, and errors can be scraped by any Prometheus-
compatible tool.

## In scope
- `app/metrics.py` — defines all metric objects at module level using the
  default `prometheus_client` registry; imported wherever metrics are
  incremented
- `app/routes/metrics.py` — `GET /metrics` returning `generate_latest()` with
  `CONTENT_TYPE_LATEST`
- Wiring in `app/main.py` to include the metrics router
- Increment sites:
  - `app/tasks/review.py` — `reviews_total` at task start;
    `review_duration_seconds` observed at task completion;
    `errors_total.labels(component="review_task")` on any unhandled exception
  - `app/llm/gemini_client.py` — `llm_calls_total` on success;
    `tokens_per_review` observed with `input_tokens + output_tokens` on success;
    `errors_total.labels(component="llm")` on any LLM exception
- Tests in `tests/test_metrics.py`

## Out of scope
- Grafana dashboards
- Multi-process mode (`PROMETHEUS_MULTIPROC_DIR`) — metrics in the Celery
  worker process are not aggregated into the API's `/metrics` in this feature;
  deferred to F28 (production-dockerfile)
- Per-repo or per-PR label dimensions on counters

## File structure
```
app/
    metrics.py              ← new
    routes/
        metrics.py          ← new
    main.py                 ← modified (include metrics router)
    tasks/
        review.py           ← modified (increment 3 metrics)
    llm/
        gemini_client.py    ← modified (increment 3 metrics)
tests/
    test_metrics.py         ← new
```

## Contracts

### `app/metrics.py`
```python
from prometheus_client import Counter, Histogram

reviews_total = Counter(
    "reviews_total",
    "PR review tasks started",
)
llm_calls_total = Counter(
    "llm_calls_total",
    "Successful Gemini API calls",
)
errors_total = Counter(
    "errors_total",
    "Errors by component",
    ["component"],           # label values: "review_task", "llm"
)
review_duration_seconds = Histogram(
    "review_duration_seconds",
    "End-to-end review task wall-clock duration",
)
tokens_per_review = Histogram(
    "tokens_per_review",
    "Total tokens (input + output) per Gemini API call",
    buckets=[128, 512, 1024, 2048, 4096, 8192, 16384],
)
```

### `GET /metrics`
- Status: 200
- `Content-Type: text/plain; version=0.0.4; charset=utf-8`
  (the value of `prometheus_client.CONTENT_TYPE_LATEST`)
- Body: Prometheus text exposition format from `generate_latest()`

### Increment sites (summary)
| Metric | Where | When |
|---|---|---|
| `reviews_total` | `review_pr` task | task body start |
| `review_duration_seconds` | `review_pr` task | task completes (success or error) |
| `errors_total[component="review_task"]` | `review_pr` task | unhandled exception |
| `llm_calls_total` | `GeminiClient._call` | after successful response |
| `tokens_per_review` | `GeminiClient._call` | after successful response |
| `errors_total[component="llm"]` | `GeminiClient._call` | any LLM exception (all 3 except blocks) |

## Dependencies
- `prometheus-client==0.21.1`

## Tests

Use `prometheus_client.generate_latest()` + `prometheus_client.REGISTRY` to
read metric text in tests, avoiding internal `_value` attribute access.
Between tests that increment counters, read before/after values by parsing
the text output or comparing collected sample values.

- `test_metrics_endpoint_returns_200`: GET /metrics via TestClient → 200,
  Content-Type starts with `"text/plain"`
- `test_metrics_endpoint_contains_all_metric_names`: response body contains
  the strings `reviews_total`, `llm_calls_total`, `errors_total`,
  `review_duration_seconds`, `tokens_per_review`
- `test_llm_calls_total_increments`: mock `generate_content` to succeed,
  call `GeminiClient.complete`, assert `llm_calls_total._value.get()` increased by 1
- `test_tokens_per_review_observed`: mock returns 10 input + 5 output tokens,
  assert `tokens_per_review._sum.get()` increased by 15
- `test_errors_total_increments_on_llm_error`: mock raises `ServerError`,
  call `complete` (suppress exception), assert
  `errors_total.labels(component="llm")._value.get()` increased

## Acceptance criteria
1. `GET /metrics` returns 200 with valid Prometheus text format
2. Response body contains all 5 metric names
3. Calling `GeminiClient.complete` (success) increments `llm_calls_total` by 1
   and observes `tokens_per_review`
4. Calling `GeminiClient.complete` (error) increments
   `errors_total{component="llm"}`
5. `pytest tests/test_metrics.py -v` → 5 tests pass
6. `pytest tests/ -v` → all existing tests pass (98 + 5)
