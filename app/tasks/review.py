import time
from pathlib import Path

import structlog

from app.analysis.aggregator import aggregate
from app.analysis.ruff_runner import run_ruff
from app.config import get_settings
from app.github.auth import GitHubAppAuth
from app.github.context import ContextExpander
from app.github.diff import fetch_pr_diff
from app.github.exceptions import FileNotFoundAtSHA
from app.github.poster import post_review
from app.llm.gemini_client import GeminiClient
from app.llm.prompt_registry import PromptRegistry
from app.llm.review_agent import run_review
from app.metrics import errors_total, review_duration_seconds, reviews_total
from app.parser.diff import parse_diff
from app.parser.hunk import symbols_touched
from app.parser.python import parse_python
from app.tasks import celery_app

logger = structlog.get_logger()

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
def review_pr(
    repo: str,
    pr_number: int,
    installation_id: int,
    head_sha: str,
    correlation_id: str | None = None,
) -> None:
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        correlation_id=correlation_id, task="review_pr"
    )
    reviews_total.inc()
    t0 = time.perf_counter()
    try:
        auth = _get_auth()
        diff_text = fetch_pr_diff(repo, pr_number, installation_id, auth=auth)
        n_files, added, removed = _summarize_diff(diff_text)
        logger.info("diff_summary", repo=repo, pr=pr_number, files=n_files, added=added, removed=removed)

        file_diffs = parse_diff(diff_text)
        py_diffs = [fd for fd in file_diffs if fd.path.endswith(".py")]

        expander = ContextExpander(auth)
        file_sources: dict[str, str] = {}
        for fd in py_diffs:
            try:
                lines = expander._fetch_lines(repo, head_sha, fd.path, installation_id)
                file_sources[fd.path] = "\n".join(lines)
            except FileNotFoundAtSHA:
                pass  # deleted file; nothing to analyse

        raw_findings = run_ruff(file_sources) if file_sources else []
        filtered_findings = aggregate(raw_findings, file_diffs)

        context_parts: list[str] = []
        for fd in py_diffs:
            if fd.path not in file_sources:
                continue
            symbols = parse_python(file_sources[fd.path])
            for hunk in fd.hunks:
                for sym in symbols_touched(hunk, symbols):
                    snippet = expander.expand_context(
                        repo, head_sha, fd.path, sym, installation_id
                    )
                    context_parts.append(f"# {fd.path}: {sym.kind} {sym.name}\n{snippet}")

        context_str = "\n\n".join(context_parts) or "No expanded context available."

        settings = get_settings()
        comments = run_review(
            diff_text,
            context_str,
            filtered_findings,
            client=GeminiClient(),
            registry=PromptRegistry(),
            model=settings.GEMINI_MODEL,
            prompt_version=1,
        )

        post_review(repo, pr_number, installation_id, comments, auth=auth)
        logger.info("review_complete", repo=repo, pr=pr_number, comments=len(comments))
    except Exception:
        errors_total.labels(component="review_task").inc()
        raise
    finally:
        review_duration_seconds.observe(time.perf_counter() - t0)
