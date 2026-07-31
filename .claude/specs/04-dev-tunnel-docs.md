# Feature 04: dev-tunnel-docs

## Goal
Document the dev tunnel setup so a developer can receive live GitHub webhook deliveries on a local server from a real test repository.

## In scope
- New `## Local Development with GitHub` section added to `README.md`
- Sub-section: **Dev tunnel** — covers `smee.io` (primary) and `cloudflared` (alternative)
  - Install steps for each option
  - Start command that forwards to `localhost:8000/webhooks/github`
  - How to find/copy the public tunnel URL
- Sub-section: **GitHub App setup checklist** — step-by-step from a clean account:
  1. Navigate to GitHub → Settings → Developer settings → GitHub Apps → New GitHub App
  2. Fill in: App name, Homepage URL (can be `http://localhost`)
  3. Webhook URL: paste the tunnel URL (smee.io channel or cloudflared URL) + `/webhooks/github`
  4. Webhook secret: generate a random value, record it — will go into `.env` as `GITHUB_WEBHOOK_SECRET`
  5. Permissions required:
     - **Pull requests**: Read & Write (to post review comments later)
     - **Contents**: Read (to fetch diffs and file source)
  6. Subscribe to events: `Pull request`
  7. Where to install: "Only on this account"
  8. After creation: generate a private key, download the `.pem` file, save its path to `.env` as `GITHUB_PRIVATE_KEY_PATH`
  9. Record the **App ID** (shown on the App settings page) → `.env` as `GITHUB_APP_ID`
- Sub-section: **Install the App on a test repo**
  - From the App's settings page → Install App → choose a repo
  - Open a test PR on that repo and confirm the delivery appears in GitHub's Recent Deliveries tab
- Sub-section: **Verify end-to-end locally**
  - Boot the server (`uvicorn app.main:app --reload`)
  - Start the tunnel
  - Open a PR (or re-deliver from Recent Deliveries)
  - Expected server log line: delivery ID, repo name, PR number

## Out of scope
- Any code changes
- Docker or production deployment (covered in Phase 9)
- smee.io client library integration in Python (optional future polish)
- Per-repo webhook configuration (GitHub App webhook covers all installed repos)
- Windows-specific shell variations beyond a brief note

## File structure
```
README.md    # modified — new "Local Development with GitHub" section appended
```

## Contracts
N/A — documentation only.

## Dependencies
None — smee.io client is installed via `npm` / `npx`, not a Python dep.

## Tests
N/A — acceptance is manual verification per the criteria below.

## Acceptance criteria
1. A developer on a clean laptop can follow the README, run the listed commands, and see a GitHub webhook delivery appear in the local server logs within 60 seconds of opening a test PR.
2. The checklist covers every required `.env` value: `GITHUB_APP_ID`, `GITHUB_WEBHOOK_SECRET`, `GITHUB_PRIVATE_KEY_PATH` (the remaining required var, `CLAUDE_API_KEY`, is left for a later feature and must be noted as "not needed yet").
3. Both smee.io and cloudflared options are shown; smee.io is marked as the recommended path.
4. The correct permissions (Pull requests R/W, Contents R) are listed so a developer does not have to guess and re-create the App later.
5. The "Verify end-to-end" step tells the reader exactly what log output to expect, so they know it worked.
