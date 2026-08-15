from datetime import UTC, datetime, timedelta

import httpx
import jwt
import structlog
from cryptography.hazmat.primitives.serialization import load_pem_private_key

logger = structlog.get_logger()

_GITHUB_API_BASE = "https://api.github.com"
_JWT_LIFETIME = timedelta(minutes=10)
_TOKEN_REFRESH_BUFFER = timedelta(minutes=5)


class GitHubAppAuth:
    def __init__(self, app_id: str, private_key: str) -> None:
        try:
            load_pem_private_key(private_key.encode(), password=None)
        except Exception as exc:
            raise ValueError(f"Invalid RSA private key: {exc}") from exc
        self._app_id = app_id
        self._private_key = private_key
        self._cache: dict[int, tuple[str, datetime]] = {}

    def _make_jwt(self) -> str:
        now = datetime.now(UTC)
        payload = {
            "iss": self._app_id,
            "iat": int(now.timestamp()),
            "exp": int((now + _JWT_LIFETIME).timestamp()),
        }
        return jwt.encode(payload, self._private_key, algorithm="RS256")

    def get_installation_token(self, installation_id: int) -> str:
        now = datetime.now(UTC)
        if installation_id in self._cache:
            token, expires_at = self._cache[installation_id]
            if expires_at - now > _TOKEN_REFRESH_BUFFER:
                return token

        response = httpx.post(
            f"{_GITHUB_API_BASE}/app/installations/{installation_id}/access_tokens",
            headers={
                "Authorization": f"Bearer {self._make_jwt()}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=10.0,
        )
        response.raise_for_status()
        data = response.json()
        token = data["token"]
        expires_at = datetime.fromisoformat(data["expires_at"])
        self._cache[installation_id] = (token, expires_at)
        logger.info("installation_token_fetched", installation_id=installation_id, expires_at=str(expires_at))
        return token
