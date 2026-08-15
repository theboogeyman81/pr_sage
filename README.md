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

## Deploying to Railway

### Prerequisites
- [Railway account](https://railway.app) (sign up with GitHub)
- Railway CLI: `npm install -g @railway/cli` then `railway login`

### 1. Create the project
1. Railway dashboard → **New Project** → **Deploy from GitHub repo** → select this repo
2. Railway detects the Dockerfile automatically and creates the app service

### 2. Add Redis
Inside the project → **New** → **Database** → **Add Redis**. Railway injects `REDIS_URL` automatically into all services.

### 3. Set secrets on the app service
Go to the app service → **Variables** and add:

| Variable | Value |
|---|---|
| `GITHUB_APP_ID` | from your GitHub App settings |
| `GITHUB_WEBHOOK_SECRET` | the secret set when creating the app |
| `GITHUB_PRIVATE_KEY` | paste the full `.pem` file contents (multiline is fine) |
| `GEMINI_API_KEY` | from Google AI Studio |

### 4. Add the worker service
1. Inside the same project → **New** → **GitHub Repo** → same repo
2. On this service → **Settings** → **Start Command**:
   ```
   celery -A app.tasks worker --loglevel=info
   ```
3. Add the same 4 variables from step 3 (`REDIS_URL` is already shared)

### 5. Verify
Both services deploy automatically on push to `main`. Check the app service URL:
```bash
curl https://<app>.railway.app/health
# → {"status":"ok"}
```

## Connecting the GitHub App (production)

Once the app is deployed and the public URL is known:

1. GitHub → Settings → Developer settings → GitHub Apps → your app → **General**
2. **Webhook URL** → `https://<app>.railway.app/webhooks/github`
3. Confirm **Webhook Secret** matches `GITHUB_WEBHOOK_SECRET`
4. **Permissions:** Pull requests (Read & Write), Contents (Read)
5. **Events:** Pull request
6. **Install App** on a test repo
7. Open a PR — the bot posts a review comment within 60 seconds
