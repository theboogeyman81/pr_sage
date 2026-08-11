# Feature 08: celery-scaffold

## Goal
Stand up a Celery app wired to Redis, with one `ping()` task that logs and returns `"pong"`, and a test that runs the task without a live broker.

## In scope
- `app/tasks/__init__.py` — `celery_app` instance + `configure_celery(redis_url)` helper
- `app/tasks/ping.py` — `ping` task that logs and returns `"pong"`
- `app/main.py` — call `configure_celery(settings.REDIS_URL)` in the lifespan so the real broker URL is applied at startup
- `tests/test_ping.py` — one test using `ping.apply()` (synchronous, no broker needed)
- `pyproject.toml` — add `celery==5.4.0` and `redis==5.2.1`

## Out of scope
- Wiring to the webhook (Feature 09)
- Any real review tasks
- Celery Beat (scheduled tasks)
- Result expiry / task routing configuration (defaults are fine for now)

## File structure
```
app/
  tasks/
    __init__.py    # new — celery_app + configure_celery()
    ping.py        # new — ping task
  main.py          # modified — configure_celery() in lifespan
tests/
  test_ping.py     # new — 1 test
pyproject.toml     # modified — celery + redis added
```

## Contracts

### `app/tasks/__init__.py`

```python
from celery import Celery

celery_app = Celery(
    "pr_sage",
    broker="redis://localhost:6379/0",   # default; overridden at startup
    backend="redis://localhost:6379/0",
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)

def configure_celery(redis_url: str) -> None:
    """Apply the real broker URL from settings. Called once at app startup."""
    celery_app.conf.broker_url = redis_url
    celery_app.conf.result_backend = redis_url
```

The Celery app is created with a hardcoded default URL so it is importable at module load time without calling `get_settings()`. This avoids a circular dependency problem: the test runner imports the module before the autouse fixture sets env vars, so `get_settings()` at module level would fail on missing required vars. `configure_celery()` is called by `app.main` at startup to apply the real URL.

### `app/tasks/ping.py`

```python
import logging
from app.tasks import celery_app

logger = logging.getLogger(__name__)

@celery_app.task(name="tasks.ping")
def ping() -> str:
    logger.info("ping task executed")
    return "pong"
```

### `app/main.py` modification

In the `lifespan` context manager, add:
```python
from app.tasks import configure_celery
...
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_celery(settings.REDIS_URL)
    yield
```

### CLI (for manual verification)
```bash
celery -A app.tasks worker --loglevel=info
```

## Dependencies

New additions to `pyproject.toml` main deps:
```
celery==5.4.0
redis==5.2.1
```

## Tests

```python
# tests/test_ping.py
from app.tasks.ping import ping

def test_ping_task():
    result = ping.apply()
    assert result.get() == "pong"
```

`ping.apply()` runs the task synchronously in the current process — no broker connection, no Redis required. This is distinct from `ping.delay()` (async, requires a running broker) and `ping()` (direct function call, bypasses Celery entirely). `apply()` exercises the full Celery task machinery without infrastructure.

## Acceptance criteria
1. `test_ping_task` passes with `pytest` (no Redis running required).
2. `celery -A app.tasks worker --loglevel=info` starts without errors when Redis is up (via `docker-compose up -d`).
3. In a Python shell with the worker running, `ping.delay().get(timeout=5)` returns `"pong"`.
4. `configure_celery()` is the only place `REDIS_URL` is applied to the Celery app — no direct env reads in `app/tasks/`.
5. All existing 16 tests remain green.
