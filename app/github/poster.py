import logging

import httpx

from app.github.auth import GitHubAppAuth
from app.github.exceptions import GitHubServerError, PRAccessDeniedError, PRNotFoundError
from app.llm.review_agent import Comment

_GITHUB_API_BASE = "https://api.github.com"
_SEVERITY_LABEL = {
    "error": "[error]",
    "warning": "[warning]",
    "suggestion": "[suggestion]",
}
logger = logging.getLogger(__name__)


def post_review(
    repo: str,
    pr_number: int,
    installation_id: int,
    comments: list[Comment],
    *,
    auth: GitHubAppAuth,
) -> None:
    """Post comments as a single GitHub PR review. No-op if comments is empty."""
    if not comments:
        return

    token = auth.get_installation_token(installation_id)
    payload = {
        "event": "COMMENT",
        "body": "",
        "comments": [
            {
                "path": c.path,
                "line": c.line,
                "side": "RIGHT",
                "body": f"{_SEVERITY_LABEL[c.severity]} {c.body}",
            }
            for c in comments
        ],
    }
    response = httpx.post(
        f"{_GITHUB_API_BASE}/repos/{repo}/pulls/{pr_number}/reviews",
        json=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        timeout=30.0,
    )
    if response.status_code == 404:
        raise PRNotFoundError(f"PR #{pr_number} not found in {repo}")
    if response.status_code == 403:
        raise PRAccessDeniedError(f"Access denied to {repo} PR #{pr_number}")
    if response.status_code >= 500:
        raise GitHubServerError(f"GitHub server error {response.status_code}")
    response.raise_for_status()
    logger.info("review_posted repo=%s pr=%s comments=%d", repo, pr_number, len(comments))
