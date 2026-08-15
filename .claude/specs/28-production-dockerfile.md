# Feature 28: production-dockerfile

## Goal
Produce a multi-stage Docker image that can run both the FastAPI app and the Celery worker from a single image, controlled by the CMD at runtime.

## In scope
- `Dockerfile` with two stages: `builder` (compiles wheels) and `runtime` (slim, non-root user)
- Builder stage: `python:3.11-slim` base, installs build deps, compiles all wheels from `pyproject.toml`
- Runtime stage: `python:3.11-slim` base, copies compiled wheels, installs them, drops to a non-root user (`appuser`, uid 1000)
- `HEALTHCHECK` instruction in the runtime stage targeting `GET /health`
- `.dockerignore` excluding `.git`, `__pycache__`, `.mypy_cache`, `.pytest_cache`, `.ruff_cache`, `.venv`, `venv`, `.env`, `eval_reports/`, `*.pem`, `*.pyc`
- Default `CMD` starts the FastAPI app: `uvicorn app.main:app --host 0.0.0.0 --port 8000`
- Worker invoked by overriding CMD at runtime: `celery -A app.tasks worker --loglevel=info`
- `docker-compose.yml` updated to add `app` and `worker` services that both build from the same image

## Out of scope
- Pushing/publishing the image to a registry
- Production secrets injection (handled in Feature 30)
- CI build of the image (handled in Feature 29)
- Multi-platform builds (`--platform`)

## File structure
```
Dockerfile           ← new
.dockerignore        ← new
docker-compose.yml   ← modified (add app + worker services)
```

## Contracts

**Dockerfile stages:**
```
FROM python:3.11-slim AS builder
  → installs gcc + build-essential
  → pip wheel --no-cache-dir --wheel-dir /wheels .

FROM python:3.11-slim AS runtime
  → copies /wheels from builder
  → pip install --no-index --find-links /wheels pr-sage
  → creates non-root user: appuser (uid=1000, gid=1000)
  → WORKDIR /app
  → copies app/, prompts/, style_guide.yaml
  → HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
      CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"
  → USER appuser
  → CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**docker-compose.yml additions:**
```yaml
services:
  app:
    build: .
    ports: ["8000:8000"]
    env_file: .env
    depends_on:
      redis: {condition: service_healthy}

  worker:
    build: .
    command: ["celery", "-A", "app.tasks", "worker", "--loglevel=info"]
    env_file: .env
    depends_on:
      redis: {condition: service_healthy}
```

## Dependencies
No new Python dependencies. Docker Engine 24+ assumed.

## Tests
No automated tests for this feature — acceptance criteria are verified manually by building and running the image.

## Acceptance criteria
1. `docker build -t pr-sage .` completes without error
2. `docker run --rm pr-sage python -c "import app.main"` exits 0 (imports work)
3. `docker run --rm -e PORT=8000 ... pr-sage` (with required env vars) → `curl localhost:8000/health` returns `{"status":"ok"}`
4. `docker run --rm pr-sage celery -A app.tasks worker --loglevel=info` starts the worker without crashing
5. The running container's process is owned by `appuser` (uid 1000), not root
6. `docker-compose up app worker` brings both services up alongside Redis
