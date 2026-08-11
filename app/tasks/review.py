import logging
from pathlib import Path

from app.config import get_settings
from app.github.auth import GitHubAppAuth
from app.github.diff import fetch_pr_diff
from app.tasks import celery_app

logger = logging.getLogger(__name__)

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
