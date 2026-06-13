# Feature 01: Project Scaffold

## Goal
A runnable FastAPI app with a `/health` endpoint, passing tests, and the
project structure that all future features will build on.

## In Scope
- Python package layout under `app/`
- `pyproject.toml` with pinned dependencies
- `GET /health` returning `{"status": "ok"}` with HTTP 200
- Centralized logging setup (stdlib `logging`, key=value format to stdout)
- One pytest test for `/health` that asserts status code AND body
- `.gitignore` (Python defaults + `.env`)
- `.env.example` with empty placeholders:
  - `GITHUB_WEBHOOK_SECRET=`
  - `GITHUB_APP_ID=`
  - `GITHUB_PRIVATE_KEY_PATH=`
- `README.md` with: project one-liner, setup commands, run command, test command

## Out of Scope
- GitHub webhook endpoint
- HMAC signature verification
- Celery, Redis, queues
- Docker, docker-compose
- GitHub App authentication
- Any LLM integration
All of the above are future features. Do not stub or import them.

## File Structure
.

├── .claude/

│   ├── specs/01-project-scaffold.md

│   └── plans/01-project-scaffold.md

├── app/

│   ├── init.py

│   ├── main.py              # FastAPI app instance + route registration

│   ├── logging_config.py    # configure_logging() called once at startup

│   └── routes/

│       ├── init.py

│       └── health.py        # /health route

├── tests/

│   ├── init.py

│   └── test_health.py

├── .env.example

├── .gitignore

├── pyproject.toml

└── README.md

## Dependencies (pinned)
- fastapi==0.115.6
- uvicorn[standard]==0.32.1
- pytest==8.3.4
- httpx==0.28.1   # for TestClient async usage

## Endpoint Contract
- `GET /health`
- Response: `200 OK`, body: `{"status": "ok"}`
- No auth, no query params, no side effects

## Logging
- Configured once in `logging_config.py` via `configure_logging()`
- Called from `app/main.py` at module import / app startup
- Format: `time=<iso8601> level=<LEVEL> logger=<name> msg=<message>`
- Output: stdout
- Default level: INFO

## Tests
- `tests/test_health.py` uses FastAPI `TestClient`
- One test: `test_health_returns_ok`
  - Asserts status code == 200
  - Asserts response JSON == `{"status": "ok"}`

## Acceptance Criteria
1. `pip install -e .` (or `pip install -r` equivalent) succeeds in a fresh venv
2. `uvicorn app.main:app --reload` boots without errors
3. `curl localhost:8000/health` returns `{"status":"ok"}` with 200
4. `pytest` runs and the one test passes
5. Log line appears on stdout when the request is served
6. No code references webhooks, Celery, GitHub auth, or Docker