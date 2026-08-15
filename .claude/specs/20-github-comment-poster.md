# Feature 20: GitHub Comment Poster

## Goal
Post the review agent's structured comments back to the PR as a single GitHub
review with all inline comments attached to the correct file and line.

## In scope
- `post_review(repo, pr_number, installation_id, comments, *, auth) -> None`
  in `app/github/poster.py`.
- Uses GitHub's **Create a Review** API:
  `POST /repos/{repo}/pulls/{pr_number}/reviews`
- One review object with N inline comments — not N separate API calls.
- Review event type: `"COMMENT"` (non-approving, non-requesting-changes).
- Each `Comment` maps to a GitHub review comment with `side: "RIGHT"` (new-file
  side), `path`, `line`, and `body`. `severity` is prepended to `body` as a
  label: `[error]`, `[warning]`, `[suggestion]`.
- If `comments` is empty, the function returns immediately without hitting the
  API (no empty review posted).
- Error handling mirrors `app/github/diff.py`:
  - 404 → `PRNotFoundError`
  - 403 → `PRAccessDeniedError`
  - 5xx → `GitHubServerError`
- Timeout: 30 s (same as `fetch_pr_diff`).
- Log one line on success: repo, PR number, comment count.

## Out of scope
- Updating or dismissing an existing review on `synchronize` events.
- Approving or requesting changes (always uses `COMMENT` event).
- Posting a top-level PR comment when there are no inline comments.
- Resolving review threads.

## File structure
```
app/
  github/
    poster.py           ← new: post_review()
tests/
  test_github_poster.py ← new
.claude/
  specs/20-github-comment-poster.md
```

No changes to existing files except `app/github/__init__.py` if it needs updating
(check at implementation time — it may be empty).

## Contracts

```python
# app/github/poster.py

import logging
import httpx

from app.github.auth import GitHubAppAuth
from app.github.exceptions import GitHubServerError, PRAccessDeniedError, PRNotFoundError
from app.llm.review_agent import Comment

_GITHUB_API_BASE = "https://api.github.com"
logger = logging.getLogger(__name__)

_SEVERITY_LABEL = {
    "error": "[error]",
    "warning": "[warning]",
    "suggestion": "[suggestion]",
}

def post_review(
    repo: str,
    pr_number: int,
    installation_id: int,
    comments: list[Comment],
    *,
    auth: GitHubAppAuth,
) -> None:
    """Post comments as a single GitHub PR review. No-op if comments is empty."""
```

### GitHub API request shape
```
POST https://api.github.com/repos/{repo}/pulls/{pr_number}/reviews
Authorization: Bearer {token}
Accept: application/vnd.github+json
X-GitHub-Api-Version: 2022-11-28

{
  "event": "COMMENT",
  "body": "",
  "comments": [
    {
      "path": "app/foo.py",
      "line": 10,
      "side": "RIGHT",
      "body": "[error] Missing return type annotation."
    },
    ...
  ]
}
```

### Comment body format
Prepend the severity label so reviewers see urgency at a glance:
`f"{_SEVERITY_LABEL[comment.severity]} {comment.body}"`

## Dependencies
None new. `httpx` is already a pinned dependency.

## Tests
All tests mock `httpx.post` via `unittest.mock.patch`. Pass a real-ish
`GitHubAppAuth` mock that returns a fixed token.

- `test_post_review_success`: mock returns 200 → function returns None, httpx.post called once with correct URL and `"event": "COMMENT"`
- `test_post_review_empty_comments_no_op`: `comments=[]` → `httpx.post` never called
- `test_post_review_body_includes_severity`: assert comment body in request JSON starts with `"[error]"` / `"[warning]"` / `"[suggestion]"` prefix
- `test_post_review_404_raises`: mock returns 404 → `PRNotFoundError`
- `test_post_review_403_raises`: mock returns 403 → `PRAccessDeniedError`
- `test_post_review_500_raises`: mock returns 500 → `GitHubServerError`

## Acceptance criteria
1. A real PR event triggers a single `POST /reviews` call (not N separate comment calls).
2. Empty `comments` list → no API call made.
3. Each comment body is prefixed with its severity label.
4. 404/403/5xx responses raise the correct typed exception.
5. All 6 tests pass with `pytest`.
6. Full suite (76 existing + 6 new) stays green.
