import httpx
import structlog

from app.github.auth import GitHubAppAuth
from app.github.exceptions import FileNotFoundAtSHA, GitHubServerError
from app.parser.python import Symbol

_GITHUB_API_BASE = "https://api.github.com"
logger = structlog.get_logger()


class ContextExpander:
    def __init__(self, auth: GitHubAppAuth) -> None:
        self._auth = auth
        self._cache: dict[tuple[str, str], list[str]] = {}

    def expand_context(
        self,
        repo: str,
        sha: str,
        path: str,
        symbol: Symbol,
        installation_id: int,
        *,
        padding: int = 10,
    ) -> str:
        lines = self._fetch_lines(repo, sha, path, installation_id)
        start = max(0, symbol.start_line - 1 - padding)
        end = min(len(lines), symbol.end_line + padding)
        return "\n".join(lines[start:end])

    def _fetch_lines(
        self, repo: str, sha: str, path: str, installation_id: int
    ) -> list[str]:
        key = (sha, path)
        if key in self._cache:
            return self._cache[key]
        token = self._auth.get_installation_token(installation_id)
        response = httpx.get(
            f"{_GITHUB_API_BASE}/repos/{repo}/contents/{path}",
            params={"ref": sha},
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github.raw+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=30.0,
        )
        if response.status_code == 404:
            raise FileNotFoundAtSHA(f"{path} not found at {sha} in {repo}")
        if response.status_code >= 500:
            raise GitHubServerError(f"GitHub server error {response.status_code}")
        response.raise_for_status()
        lines = response.text.splitlines()
        self._cache[key] = lines
        logger.debug("context_fetched", repo=repo, sha=sha[:8], path=path, lines=len(lines))
        return lines
