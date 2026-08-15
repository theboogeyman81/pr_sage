# Feature 30: cloud-deploy

## Goal
Ship `railway.json` and a Railway setup guide so the app and worker can be deployed to Railway with a public URL.

## In scope
- `railway.json` — build + deploy config for the app service (Railway reads this for the web process)
- README section "Deploying to Railway" covering: account setup, CLI install, creating services, setting secrets, pointing at Redis, verifying `/health`
- Worker is a second Railway service sharing the same repo + Dockerfile, with `startCommand` overridden to `celery -A app.tasks worker --loglevel=info`

## Out of scope
- High availability / scaling
- Custom domain setup
- CI-triggered deploys (Railway auto-deploys from GitHub by default)
- Fly.io config

## File structure
```
railway.json          ← new
README.md             ← modified (add "Deploying to Railway" section)
```

## Contracts

### `railway.json`
```json
{
  "$schema": "https://railway.com/railway.schema.json",
  "build": {
    "builder": "DOCKERFILE"
  },
  "deploy": {
    "startCommand": "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}",
    "healthcheckPath": "/health",
    "healthcheckTimeout": 30
  }
}
```
Railway injects `$PORT` at runtime; the `${PORT:-8000}` fallback keeps local `docker run` working.

### Required Railway env vars (set in dashboard)
| Variable | Value |
|---|---|
| `GITHUB_APP_ID` | from GitHub App settings |
| `GITHUB_WEBHOOK_SECRET` | from GitHub App settings |
| `GITHUB_PRIVATE_KEY` | full PEM content (Railway supports multiline) |
| `GEMINI_API_KEY` | from Google AI Studio |
| `REDIS_URL` | auto-set by Railway Redis plugin |

`REDIS_URL` is injected automatically when you add the Railway Redis plugin — no manual entry needed.

### Worker service
Created manually in Railway dashboard: same repo, same Dockerfile, `startCommand` overridden to:
```
celery -A app.tasks worker --loglevel=info
```
All env vars shared via Railway's "shared variables" feature.

## Dependencies
No new Python packages. Railway CLI: `npm install -g @railway/cli` (user installs).

## Tests
No automated tests — acceptance is verified by hitting the deployed URL.

## Acceptance criteria
1. `https://<app>.railway.app/health` returns `{"status":"ok"}`
2. Worker service is running and logs are visible in Railway dashboard
3. README deploy section is complete enough to follow from scratch
