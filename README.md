# pr_sage

AI-powered pull request review assistant built on FastAPI and GitHub Apps.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # fill in your values
```

## Local services

Redis is required for the async task queue (Phase 3+). Start it with Docker Compose:

**Prerequisites:** [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Mac/Windows) or Docker Engine + Compose plugin (Linux).

```bash
# Start Redis in the background
docker-compose up -d

# Verify it's healthy
docker-compose exec redis redis-cli ping
# → PONG

# Stop (data volume persists)
docker-compose down

# Stop and wipe data
docker-compose down -v
```

`REDIS_URL` defaults to `redis://localhost:6379/0` — no `.env` change needed for local dev.

## Run

```bash
uvicorn app.main:app --reload
```

## Test

```bash
pytest
```
