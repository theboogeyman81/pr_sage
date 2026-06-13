# Implementation Plan: 01-Project-Scaffold

## Context
This is the foundational scaffold for **pr_sage**, a FastAPI application that will eventually
process GitHub webhooks and integrate with LLMs. Feature 01 establishes the project layout,
packaging, logging, and a single health-check endpoint so every subsequent feature has a
stable base to build on.

---

## File Tree

```
pr_sage/
├── .claude/
│   ├── specs/01-project-scaffold.md   # source spec (already exists)
│   └── plans/01-project-scaffold.md   # this file
├── app/
│   ├── __init__.py                    # empty package marker
│   ├── main.py                        # FastAPI instance + startup + route registration
│   ├── logging_config.py              # configure_logging() helper
│   └── routes/
│       ├── __init__.py                # empty package marker
│       └── health.py                  # GET /health route
├── tests/
│   ├── __init__.py                    # empty package marker
│   └── test_health.py                 # pytest suite for /health
├── .env.example                       # placeholder env vars
├── .gitignore                         # Python defaults + .env
├── pyproject.toml                     # packaging + pinned dependencies
└── README.md                          # one-liner, setup/run/test commands
```

---

## File Purposes

| File | Purpose |
|---|---|
| `app/__init__.py` | Empty; makes `app/` importable as a Python package |
| `app/main.py` | Creates `FastAPI()` instance, calls `configure_logging()` at module import, includes health router |
| `app/logging_config.py` | `configure_logging()`: attaches a stdout `StreamHandler` with a key=value `Formatter` |
| `app/routes/__init__.py` | Empty package marker |
| `app/routes/health.py` | `APIRouter` with `GET /health`; returns `{"status": "ok"}`; emits one INFO log per request |
| `tests/__init__.py` | Empty package marker |
| `tests/test_health.py` | `test_health_returns_ok` using synchronous `TestClient` |
| `pyproject.toml` | PEP 517/518 build config; runtime + dev deps; pytest `testpaths` config |
| `.env.example` | Documents required env vars with empty values |
| `.gitignore` | Standard Python ignores plus `.env` |
| `README.md` | One-liner description, venv setup, run command, test command |

---

## Pinned Dependencies

### Runtime — `[project] dependencies`
```
fastapi==0.115.6
uvicorn[standard]==0.32.1
```

### Dev/test — `[project.optional-dependencies] dev`
```
pytest==8.3.4
httpx==0.28.1
```

**Build backend:** `hatchling` (lightweight, zero-config for a simple package layout).

**Python floor:** `requires-python = ">=3.11"` (assumption — see ambiguities).

**Install command:** `pip install -e ".[dev]"`

---

## `/health` Response Shape

```
GET /health HTTP/1.1

HTTP/1.1 200 OK
Content-Type: application/json

{"status": "ok"}
```

- No query parameters
- No request body
- No authentication
- No side effects beyond the log line

---

## Logging Setup

### `app/logging_config.py`

```
configure_logging()
  └── logging.getLogger()          # root logger
       ├── .handlers.clear()       # remove any default handlers
       ├── .addHandler(handler)    # StreamHandler(sys.stdout)
       └── .setLevel(INFO)

KeyValueFormatter(logging.Formatter)
  └── format(record) →
        "time=<iso8601> level=<LEVEL> logger=<name> msg=<message>"
```

- **Timestamp**: `datetime.now(timezone.utc).isoformat()` — UTC with `+00:00` offset (unambiguous ISO 8601).
- **Call site**: Called top-level in `app/main.py` at module import (not inside a startup event), so logging is active before any request arrives.

### Example log line
```
time=2026-06-12T10:00:00.123456+00:00 level=INFO logger=app.routes.health msg=health check
```

---

## Pytest Test Cases

**File:** `tests/test_health.py`

Uses synchronous `TestClient` from `fastapi.testclient` (wraps httpx internally; no async
test runner or `anyio` needed).

| Test name | Setup | Assertions |
|---|---|---|
| `test_health_returns_ok` | `client = TestClient(app)` → `response = client.get("/health")` | `response.status_code == 200` AND `response.json() == {"status": "ok"}` |

`pyproject.toml` will set:
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
```

---

## Verification Steps

1. `python -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"` — completes without errors.
2. `uvicorn app.main:app --reload` — server starts; a startup log line is visible on stdout.
3. `curl -s http://localhost:8000/health` — returns `{"status":"ok"}` with 200.
4. `pytest` — `1 passed, 0 errors`.
5. `grep -rE "webhook|celery|redis|docker|github_app|openai|anthropic" app/` — returns nothing.
