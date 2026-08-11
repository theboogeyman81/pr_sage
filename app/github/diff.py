import httpx
import structlog

from app.github.auth import GitHubAppAuth
from app.github.exceptions import GitHubServerError, PRAccessDeniedError, PRNotFoundError

logger = structlog.get_logger()

_GITHUB_API_BASE = "https://api.github.com"


def fetch_pr_diff(
    repo: str,
    pr_number: int,
    installation_id: int,
    *,
    auth: GitHubAppAuth,
) -> str:
    token = auth.get_installation_token(installation_id)
    response = httpx.get(
        f"{_GITHUB_API_BASE}/repos/{repo}/pulls/{pr_number}",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3.diff",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        timeout=30.0,
    )
    if response.status_code == 404:
        raise PRNotFoundError(f"PR #{pr_number} not found in {repo}")
    if response.status_code == 403:
        raise PRAccessDeniedError(f"Access denied to {repo} PR #{pr_number}")
    if response.status_code >= 500:
        raise GitHubServerError(f"GitHub server error {response.status_code} for {repo} PR #{pr_number}")
    response.raise_for_status()
    diff = response.text
    logger.info("pr_diff_fetched", repo=repo, pr=pr_number, bytes=len(diff))
    return diff
