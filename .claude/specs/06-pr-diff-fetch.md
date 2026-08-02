# Feature 06: pr-diff-fetch

## Goal
Given a repo name, PR number, installation ID, and an auth instance, fetch the PR's raw unified diff from the GitHub API and return it as a string.

## In scope
- `app/github/exceptions.py` — typed exception hierarchy for GitHub API failures
- `app/github/diff.py` — `fetch_pr_diff(repo, pr_number, installation_id, *, auth)` function
- Tests with mocked HTTP — no real GitHub calls

## Out of scope
- Parsing the diff (Feature 11)
- Retry logic on 5xx (no retries in this feature; added in Feature 17's ClaudeClient pattern if needed)
- Caching diffs
- Fetching file contents or the full PR object — only the unified diff

## File structure
```
app/
  github/
    __init__.py       # exists
    auth.py           # exists — GitHubAppAuth
    exceptions.py     # new — typed exception hierarchy
    diff.py           # new — fetch_pr_diff
tests/
  test_pr_diff_fetch.py  # new — 4 tests
```

## Contracts

### `app/github/exceptions.py`

```python
class GitHubAPIError(Exception):
    """Base class for all GitHub API errors raised by this project."""

class PRNotFoundError(GitHubAPIError):
    """Raised on 404 — PR or repo does not exist or is not visible to the installation."""

class PRAccessDeniedError(GitHubAPIError):
    """Raised on 403 — installation token lacks the required permissions."""

class GitHubServerError(GitHubAPIError):
    """Raised on 5xx — GitHub-side failure."""
```

Callers may catch `GitHubAPIError` to handle all GitHub failures uniformly, or catch specific subclasses for differentiated handling.

### `app/github/diff.py`

```python
def fetch_pr_diff(
    repo: str,
    pr_number: int,
    installation_id: int,
    *,
    auth: GitHubAppAuth,
) -> str:
    """
    repo: full repo name in "owner/repo" format (from webhook payload's repository.full_name)
    pr_number: integer PR number
    installation_id: GitHub App installation ID (from webhook payload's installation.id)
    auth: caller-supplied GitHubAppAuth instance (preserves token cache across calls)

    Returns the raw unified diff string.

    Raises:
        PRNotFoundError     on 404
        PRAccessDeniedError on 403
        GitHubServerError   on 5xx
    """
```

GitHub API call:
```
GET https://api.github.com/repos/{repo}/pulls/{pr_number}
Headers:
  Authorization: Bearer <installation_token>
  Accept: application/vnd.github.v3.diff
  X-GitHub-Api-Version: 2022-11-28
Timeout: 30s
Response: raw unified diff text (Content-Type: text/x-patch or text/plain)
```

## Dependencies
- None new — `httpx==0.28.1` already in main deps from F05

## Tests

Fixtures:
- `auth_mock` — a `MagicMock` standing in for `GitHubAppAuth`; `auth_mock.get_installation_token.return_value = "tok_test"`

Tests:
- `test_fetch_pr_diff_success` — patches `httpx.get` returning a 200 response whose `.text` is `"--- a/foo.py\n+++ b/foo.py\n@@ ..."`, calls `fetch_pr_diff("owner/repo", 7, 42, auth=auth_mock)`, asserts return value equals that diff string and the correct URL + headers were passed to `httpx.get`
- `test_fetch_pr_diff_404` — patches `httpx.get` returning status 404, asserts `PRNotFoundError` is raised
- `test_fetch_pr_diff_403` — patches `httpx.get` returning status 403, asserts `PRAccessDeniedError` is raised
- `test_fetch_pr_diff_5xx` — patches `httpx.get` returning status 500, asserts `GitHubServerError` is raised

## Acceptance criteria
1. All 4 tests pass.
2. A 404 from GitHub raises `PRNotFoundError`; a 403 raises `PRAccessDeniedError`; a 5xx raises `GitHubServerError` — never a raw `httpx` exception for these three cases.
3. The `Accept: application/vnd.github.v3.diff` header is present on every request (verified in `test_fetch_pr_diff_success`).
4. `auth.get_installation_token(installation_id)` is called exactly once per `fetch_pr_diff` invocation — the function does not construct its own `GitHubAppAuth`.
5. `httpx` timeout is set to 30 seconds (diffs can be large).
6. Log line on success includes repo, PR number, and diff size in bytes.
