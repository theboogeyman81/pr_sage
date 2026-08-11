# Feature 22: Structured Logging

## Goal
Replace the custom stdlib logging formatter with structlog so every log line is
JSON-formatted and carries a correlation ID that links all log lines from a
single PR review across the API server and Celery worker.

## In scope
- `configure_logging()` in `app/logging_config.py` rewritten to configure
  structlog with JSON output and `contextvars` support.
- `CorrelationMiddleware` in `app/middleware/correlation.py` — FastAPI
  middleware that generates a `request_id` UUID per request, binds it via
  `structlog.contextvars`, and clears the context after the response.
- `app/main.py` — register `CorrelationMiddleware`.
- All 9 files currently using `logging.getLogger` switched to
  `structlog.get_logger()`. Log call signatures stay the same (keyword args).
- `app/routes/webhooks.py` — read the current `request_id` from
  `structlog.contextvars` and pass it as `correlation_id=` kwarg to
  `review_pr.delay()`.
- `app/tasks/review.py` — `review_pr` task accepts optional `correlation_id`
  kwarg, clears contextvars, then binds `correlation_id` and `task="review_pr"`
  at the top of the task body.
- Tests: middleware sets a request_id, task binds correlation_id, configure_logging
  runs cleanly.

## Out of scope
- Log shipping to an external sink (Datadog, Loki, etc.) — that is F30 (deploy).
- Per-module log level configuration.
- Async Celery signals (use simple kwarg passing, not Celery headers/signals).

## File structure
```
app/
  logging_config.py          ← rewritten: structlog config
  main.py                    ← add CorrelationMiddleware
  middleware/
    __init__.py              ← new (empty)
    correlation.py           ← new: CorrelationMiddleware
  github/
    auth.py                  ← switch to structlog.get_logger()
    diff.py                  ← switch to structlog.get_logger()
    context.py               ← switch to structlog.get_logger()
    poster.py                ← switch to structlog.get_logger()
  routes/
    health.py                ← switch to structlog.get_logger()
    webhooks.py              ← switch + pass correlation_id to task
  tasks/
    ping.py                  ← switch to structlog.get_logger()
    review.py                ← switch + bind correlation_id in task body
tests/
  test_structured_logging.py ← new
.claude/
  specs/22-structured-logging.md
```

## Contracts

### `app/logging_config.py`
```python
import logging
import structlog

def configure_logging() -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )
```

### `app/middleware/correlation.py`
```python
import uuid
import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

class CorrelationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=str(uuid.uuid4()))
        response = await call_next(request)
        structlog.contextvars.clear_contextvars()
        return response
```

### `app/main.py` change
```python
from app.middleware.correlation import CorrelationMiddleware
app.add_middleware(CorrelationMiddleware)
```

### Logger migration pattern (all 9 files)
```python
# Before
import logging
logger = logging.getLogger(__name__)

# After
import structlog
logger = structlog.get_logger()
```
Log call sites stay identical: `logger.info("msg", key=val)`.

### Correlation ID propagation

In `app/routes/webhooks.py`:
```python
from structlog.contextvars import get_merged_contextvars
...
ctx = get_merged_contextvars(structlog.get_logger())
review_pr.delay(repo, pr_number, installation_id,
                correlation_id=ctx.get("request_id"))
```

In `app/tasks/review.py`:
```python
def review_pr(repo: str, pr_number: int, installation_id: int,
              correlation_id: str | None = None) -> None:
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        correlation_id=correlation_id, task="review_pr"
    )
    ...
```

## Dependencies
- `structlog==25.4.0` — add to `pyproject.toml`

## Tests
- `test_configure_logging_runs` — `configure_logging()` completes without error
- `test_middleware_binds_request_id` — use FastAPI `TestClient`; add a test
  route that returns `get_merged_contextvars(logger)` as JSON; assert `request_id`
  key is present and is a valid UUID string
- `test_review_pr_task_receives_correlation_id` — call `review_pr` in eager mode
  with a mock for `fetch_pr_diff`; assert the task doesn't crash when
  `correlation_id="test-id"` is passed

## Acceptance criteria
1. Every log line produced by a single PR webhook event shares the same
   `request_id` value across API and worker.
2. `CorrelationMiddleware` clears the context before and after each request.
3. All 3 tests pass with `pytest`.
4. Full suite (89 existing + 3 new) stays green.
5. `structlog==25.4.0` pinned in `pyproject.toml`.
