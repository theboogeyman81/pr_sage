# Feature 03: webhook-receiver

## Goal
`POST /webhooks/github` accepts GitHub PR events, verifies HMAC-SHA256 signatures, and returns fast with appropriate status codes.

## In scope
- `app/routes/webhooks.py` — new router with `POST /webhooks/github`
- Read raw request body once; verify `X-Hub-Signature-256` header using `hmac.compare_digest` against `GITHUB_WEBHOOK_SECRET` from `get_settings()`
- Return **401** if signature is missing or invalid
- Filter on `X-GitHub-Event` header + `action` field in the JSON body:
  - `X-GitHub-Event: pull_request` AND `action` in `{opened, synchronize, reopened}` → log and return **200**
  - Any other event type or action → return **204**
- Log on handled events: `X-GitHub-Delivery` header (delivery ID), repo full name (`repository.full_name`), PR number (`pull_request.number`)
- Wire the new router into `app/main.py`
- Tests: valid signature + handled event → 200, forged signature → 401, ignored event (valid sig but `action=closed`) → 204

## Out of scope
- Enqueueing any work — just log and return
- Parsing the diff or touching GitHub API
- Handling event types other than `pull_request` in any special way

## File structure
```
app/
  routes/
    webhooks.py      # new — POST /webhooks/github
  main.py            # modified — include webhooks router
tests/
  test_webhooks.py   # new — 3 tests
```

## Contracts

```python
# app/routes/webhooks.py
from fastapi import APIRouter, Request, Response

router = APIRouter()

@router.post("/webhooks/github", status_code=200)
async def github_webhook(request: Request) -> Response: ...
```

HMAC verification (internal helper, not exported):
```python
def _verify_signature(secret: str, body: bytes, header: str | None) -> bool:
    # returns False if header is None or comparison fails
    # header format: "sha256=<hex>"
```

## Dependencies
- None (stdlib only: `hashlib`, `hmac`, `json`, `logging`)

## Tests

```python
# helpers used across all 3 tests
def _sign(body: bytes, secret: str) -> str:
    mac = hmac.new(secret.encode(), body, hashlib.sha256)
    return f"sha256={mac.hexdigest()}"
```

- `test_valid_signature_handled_event`: POST with correctly signed body, `X-GitHub-Event: pull_request`, `action=opened` → 200
- `test_forged_signature`: POST with wrong signature → 401
- `test_ignored_event`: POST with correctly signed body, `X-GitHub-Event: pull_request`, `action=closed` → 204

## Acceptance criteria
1. All 3 tests pass
2. Endpoint returns in < 100ms locally (no blocking I/O on the hot path)
3. A forged or missing `X-Hub-Signature-256` always returns 401 — never 200 or 204
4. Log line on a handled event includes delivery ID, repo name, and PR number
5. `hmac.compare_digest` is used for signature comparison (not `==`)
