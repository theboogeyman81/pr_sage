class GitHubAPIError(Exception):
    """Base class for all GitHub API errors raised by this project."""


class PRNotFoundError(GitHubAPIError):
    """Raised on 404 — PR or repo not found or not visible to the installation."""


class PRAccessDeniedError(GitHubAPIError):
    """Raised on 403 — installation token lacks required permissions."""


class GitHubServerError(GitHubAPIError):
    """Raised on 5xx — GitHub-side failure."""


class FileNotFoundAtSHA(GitHubAPIError):
    """Raised on 404 — file path not found at the given commit SHA."""
