# Feature 09: webhook-enqueue

## Goal
The webhook handler enqueues a `review_pr` Celery task instead of just logging; the task fetches the PR diff and logs a summary of files changed and lines added/removed.

## In scope
- `app/tasks/review.py` — `review_pr(repo, pr_number, installation_id)` task with lazy `_get_auth()` helper and `_summarize_diff()` helper
- `app/routes/webhooks.py` — extract `installation_id` from payload, replace the log statement with `review_pr.delay(...)`
- `tests/test_webhook_enqueue.py` — one integration test using Celery eager mode
- This feature resolves the tech debt logged as `[F05+F06→F09]`: a lazily-initialized module-level `GitHubAppAuth` singleton in the task module serves as the shared instance within a worker process

## Out of scope
- Actually reviewing the PR — just fetch and summarize the diff
- Cross-worker token cache sharing (still in-process only)
- Error handling inside the task beyond logging (retries, dead-letter queue)

## File structure
```
app/
  tasks/
    review.py       # new — review_pr task
  routes/
    webhooks.py     # modified — enqueue instead of log
tests/
  test_webhook_enqueue.py  # new — 1 integration test
```

## Contracts

### `app/tasks/review.py`

```python
# Module-level lazy singleton — created on first task execution, not at import time.
# This avoids calling get_settings() before test fixtures set env vars.
_auth: GitHubAppAuth | None = None

def _get_auth() -> GitHubAppAuth:
    global _auth
    if _auth is None:
        settings = get_settings()
        _auth = GitHubAppAuth(
            app_id=settings.GITHUB_APP_ID,
            private_key=Path(settings.GITHUB_PRIVATE_KEY_PATH).read_text(),
        )
    return _auth

def _summarize_diff(diff: str) -> tuple[int, int, int]:
    """Returns (files_changed, lines_added, lines_removed)."""
    lines = diff.splitlines()
    files   = sum(1 for l in lines if l.startswith("diff --git"))
    added   = sum(1 for l in lines if l.startswith("+") and not l.startswith("+++"))
    removed = sum(1 for l in lines if l.startswith("-") and not l.startswith("---"))
    return files, added, removed

@celery_app.task(name="tasks.review_pr")
def review_pr(repo: str, pr_number: int, installation_id: int) -> None:
    diff = fetch_pr_diff(repo, pr_number, installation_id, auth=_get_auth())
    files, added, removed = _summarize_diff(diff)
    logger.info(
        "diff_summary repo=%s pr=%s files=%d added=%d removed=%d",
        repo, pr_number, files, added, removed,
    )
```

### `app/routes/webhooks.py` change

Replace the existing log-and-return block with:
```python
from app.tasks.review import review_pr

# inside github_webhook, after the handled-event check:
installation_id = payload.get("installation", {}).get("id", 0)
review_pr.delay(repo, pr_number, installation_id)
# keep the existing logger.info line for the delivery receipt
return Response(status_code=200)
```

The existing `logger.info(...)` line stays — it logs the delivery receipt immediately (before the task runs). Only the `return` moves to after the `.delay()` call.

## Dependencies
No new packages — `celery`, `redis`, `httpx`, `PyJWT`, `cryptography` are all already in main deps.

## Tests

### `tests/test_webhook_enqueue.py`

```python
@pytest.fixture(autouse=True)
def _celery_eager():
    celery_app.conf.task_always_eager = True
    yield
    celery_app.conf.task_always_eager = False
```

`task_always_eager = True` makes `.delay()` execute synchronously in-process — no Redis or worker needed.

**`test_webhook_enqueues_review_pr`**:
- Patches `app.tasks.review._get_auth` → returns a `MagicMock()` (avoids reading the private key file)
- Patches `app.tasks.review.fetch_pr_diff` → returns a fixed fake diff with 1 file, 1 added line
- POSTs a valid signed `pull_request / opened` payload (with `installation.id = 42`) to `/webhooks/github`
- Asserts response is 200
- Asserts `fetch_pr_diff` was called once with `repo="owner/repo"`, `pr_number=7`, `installation_id=42`

Reuses `_sign()` helper pattern from `tests/test_webhooks.py`.

## Acceptance criteria
1. `test_webhook_enqueues_review_pr` passes with `pytest`.
2. All 17 existing tests remain green (the 3 webhook tests must still pass — signature and ignored-event behaviour is unchanged).
3. A valid PR webhook event causes `review_pr.delay()` to be called — the handler returns 200 without waiting for the diff fetch to complete (in production; in tests, eager mode makes it synchronous).
4. The log line from `_summarize_diff` includes `repo`, `pr`, `files`, `added`, `removed`.
5. `_get_auth()` is never called at import time — only on first task execution.
