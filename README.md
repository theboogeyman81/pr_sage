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

## Deploying to Fly.io

### Prerequisites
- [Fly.io account](https://fly.io) (sign up free)
- flyctl CLI:
  - Windows: `winget install -e --id Fly.io.flyctl`
  - Mac/Linux: `curl -L https://fly.io/install.sh | sh`
- Then: `fly auth login`

### 1. Create the app
```bash
fly launch --no-deploy
```
When prompted, choose a name (e.g. `pr-sage`) and region. This updates `fly.toml` with your chosen name.

### 2. Create Redis
```bash
fly redis create
```
Choose a name and the free Upstash plan. Copy the `REDIS_URL` from the output.

### 3. Set secrets
```bash
fly secrets set \
  GITHUB_APP_ID=your_app_id \
  GITHUB_WEBHOOK_SECRET=your_webhook_secret \
  GEMINI_API_KEY=your_gemini_key \
  REDIS_URL=redis://...
```

For the private key (paste the full `.pem` contents):
```bash
# PowerShell
fly secrets set GITHUB_PRIVATE_KEY=(Get-Content pr-sage-bot.pem -Raw)

# bash/zsh
fly secrets set GITHUB_PRIVATE_KEY="$(cat pr-sage-bot.pem)"
```

### 4. Deploy
```bash
fly deploy
```

### 5. Start the worker
```bash
fly scale count worker=1
```

### 6. Verify
```bash
fly status
curl https://<your-app>.fly.dev/health
# → {"status":"ok"}
```

To tail logs: `fly logs`

## Connecting the GitHub App (production)

Once the app is deployed and the public URL is known:

1. GitHub → Settings → Developer settings → GitHub Apps → your app → **General**
2. **Webhook URL** → `https://<your-app>.fly.dev/webhooks/github`
3. Confirm **Webhook Secret** matches `GITHUB_WEBHOOK_SECRET`
4. **Permissions:** Pull requests (Read & Write), Contents (Read)
5. **Events:** Pull request
6. **Install App** on a test repo
7. Open a PR — the bot posts a review comment within 60 seconds
