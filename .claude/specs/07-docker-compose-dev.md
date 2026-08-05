# Feature 07: docker-compose-dev

## Goal
`docker-compose up -d` brings up a Redis 7 instance for local development, with a healthcheck and a named volume for persistence.

## In scope
- `docker-compose.yml` — Redis 7 service with port mapping, named volume, and healthcheck
- `README.md` — new "Local services" section documenting how to start, stop, and verify Redis

## Out of scope
- Running the FastAPI app or Celery worker in Docker (Feature 28 — production-dockerfile)
- Any Python code changes
- `.env` changes — `REDIS_URL` already defaults to `redis://localhost:6379/0` in `app/config.py`

## File structure
```
docker-compose.yml   # new
README.md            # modified — new "Local services" section
```

## Contracts

### `docker-compose.yml`
```yaml
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

volumes:
  redis_data:
```

- `redis:7-alpine` — pinned to major version 7; alpine keeps the image small
- Port `6379` mapped to host so `redis-cli` and the app can reach it without extra config
- Named volume `redis_data` — survives `docker-compose down`; removed only with `docker-compose down -v`
- Healthcheck uses `redis-cli ping` — same command developers use to verify manually

### `README.md` addition — "Local services" section
Placed after the existing "Setup" section, before "Run". Covers:
- Prerequisites: Docker Desktop (or Docker Engine + Compose plugin)
- Start Redis: `docker-compose up -d`
- Verify: `docker-compose exec redis redis-cli ping` → `PONG`  
  (alternative if redis-cli installed locally: `redis-cli ping`)
- Stop: `docker-compose down` (data persists) · `docker-compose down -v` (wipe data)
- Note: `REDIS_URL` defaults to `redis://localhost:6379/0` — no `.env` change needed for local dev

## Dependencies
None — no new Python packages. Docker and Docker Compose are external prerequisites, not pip deps.

## Tests
N/A — acceptance is manual verification per the criteria below.

## Acceptance criteria
1. `docker-compose up -d` completes without errors and `docker-compose ps` shows the `redis` service as healthy.
2. `docker-compose exec redis redis-cli ping` returns `PONG`.
3. After `docker-compose down` followed by `docker-compose up -d`, data written before the restart is still present (volume persists).
4. The README "Local services" section provides all commands a developer needs without referring to external docs.
5. No Python files modified — existing `pytest` suite still passes unchanged.
