# Feature 31: github-app-prod

## Goal
Point the real GitHub App at the deployed Railway URL and prove end-to-end: a PR on a real repo gets a review comment from the bot within 60 seconds.

## In scope
- README section "Connecting the GitHub App" — step-by-step checklist for updating webhook URL, installing on a test repo, and verifying delivery
- No code changes required

## Out of scope
- Onboarding other users/repos
- GitHub App Marketplace listing

## File structure
```
README.md    ← modified (add "Connecting the GitHub App" section)
```

## Contracts
None — this feature is configuration-only.

### Checklist (goes into README)
1. Open GitHub App settings → General → Webhook URL → set to `https://<app>.railway.app/webhooks/github`
2. Confirm Webhook Secret matches `GITHUB_WEBHOOK_SECRET` env var on Railway
3. Permissions required: Pull requests (Read & Write), Contents (Read)
4. Events subscribed: Pull request
5. Install the app on a test repo (GitHub App settings → Install App)
6. Open a PR on the test repo
7. Verify: Railway app logs show the delivery ID + repo + PR#
8. Verify: PR gets a review comment within 60 seconds

## Dependencies
None.

## Tests
Manual only — open a real PR and observe the comment.

## Acceptance criteria
1. A PR on a real test repo receives a review comment from the bot within 60 seconds
2. Railway worker logs show the task completed for that PR
