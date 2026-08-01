# Feature 05: github-app-auth

## Goal
Given `GITHUB_APP_ID` and a private key file, produce a GitHub installation access token for a given `installation_id`, caching it until near-expiry.

## In scope
- `app/github/__init__.py` — empty package marker
- `app/github/auth.py` — `GitHubAppAuth` class
  - `__init__(self, app_id: str, private_key: str)` — accepts the RSA private key as a PEM string (pre-loaded by the caller), validates it can be parsed
  - `_make_jwt(self) -> str` — creates an RS256-signed JWT with `iss=app_id`, `iat=now`, `exp=now+10min`; used internally and in tests
  - `get_installation_token(self, installation_id: int) -> str` — returns a cached token if valid (more than 5 min remaining), otherwise calls `POST https://api.github.com/app/installations/{installation_id}/access_tokens` with the JWT, caches and returns the new token
  - In-memory cache: `dict[int, tuple[str, datetime]]` mapping `installation_id → (token, expires_at)` stored on the instance
- Move `httpx` from dev-only to main dependencies (needed at runtime for GitHub API calls)
- Tests: 4 tests with a real RSA key generated in the test fixture (no mocking of crypto)

## Out of scope
- Using the token to make any GitHub API calls (Feature 06)
- Process-wide / cross-worker token sharing (each worker instance has its own cache; acceptable for Phase 3)
- Token revocation or refresh on 401 (not needed yet)
- GitHub App installation listing or lookup

## File structure
```
app/
  github/
    __init__.py       # new — empty package marker
    auth.py           # new — GitHubAppAuth class
tests/
  test_github_auth.py # new — 4 tests
pyproject.toml        # modified — httpx moved to main deps; PyJWT + cryptography added
```

## Contracts

```python
# app/github/auth.py

class GitHubAppAuth:
    def __init__(self, app_id: str, private_key: str) -> None:
        """
        app_id: GitHub App ID (the integer shown on the App settings page, passed as str)
        private_key: RSA private key PEM contents (not a file path — caller loads the file)
        Raises ValueError if private_key cannot be parsed as an RSA key.
        """

    def _make_jwt(self) -> str:
        """Returns a signed RS256 JWT valid for 10 minutes."""

    def get_installation_token(self, installation_id: int) -> str:
        """
        Returns an installation access token.
        Hits GitHub API at most once per installation_id per ~55 minutes.
        Raises httpx.HTTPStatusError on non-2xx GitHub response.
        """
```

GitHub API call made inside `get_installation_token`:
```
POST https://api.github.com/app/installations/{installation_id}/access_tokens
Headers:
  Authorization: Bearer <JWT>
  Accept: application/vnd.github+json
  X-GitHub-Api-Version: 2022-11-28
Response body (relevant fields):
  {"token": "<string>", "expires_at": "<ISO-8601 UTC string>", ...}
```

Private key loading (caller's responsibility — done in the factory / test fixture):
```python
# How to construct from settings — not part of this feature's public API,
# but this pattern will be used by Feature 06:
from pathlib import Path
from app.config import get_settings
from app.github.auth import GitHubAppAuth

settings = get_settings()
auth = GitHubAppAuth(
    app_id=settings.GITHUB_APP_ID,
    private_key=Path(settings.GITHUB_PRIVATE_KEY_PATH).read_text(),
)
```

## Dependencies

New additions to `pyproject.toml`:
```
# main deps (move httpx from dev):
httpx==0.28.1

# new main deps:
PyJWT==2.9.0
cryptography==44.0.3
```

`PyJWT` uses the `cryptography` package as its RS256 backend; both must be in main deps.

## Tests

Test fixture (shared across all 4 tests):
```python
@pytest.fixture(scope="module")
def rsa_key_pair():
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    )
    return pem.decode()
```

- `test_make_jwt_claims`: calls `auth._make_jwt()`, decodes without verification, asserts `iss == app_id`, `exp - iat == 600` (10 minutes), `exp > now`.
- `test_get_installation_token_calls_github`: mocks `httpx.post` to return `{"token": "tok_abc", "expires_at": "<1 hour from now>"}`, calls `get_installation_token(42)`, asserts return value is `"tok_abc"` and `httpx.post` was called exactly once.
- `test_get_installation_token_cache_hit`: after the mock call above returns the token, calls `get_installation_token(42)` a second time, asserts `httpx.post` is still called exactly once (cache hit).
- `test_get_installation_token_cache_miss_after_expiry`: sets `expires_at` to 3 minutes from now (below the 5-minute buffer), calls `get_installation_token(42)` again, asserts `httpx.post` is called a second time (cache miss).

## Acceptance criteria
1. All 4 tests pass with `pytest`.
2. The second call to `get_installation_token` for the same `installation_id` within the token's lifetime does not make an HTTP request.
3. A call when the cached token has fewer than 5 minutes remaining triggers a fresh GitHub API request.
4. `_make_jwt` produces a JWT whose decoded `iss` matches the `app_id` passed to the constructor.
5. Constructing `GitHubAppAuth` with an invalid PEM string raises `ValueError` immediately (fail fast, not on first token request).
6. `httpx` is importable at runtime (not dev-only); `PyJWT` and `cryptography` are pinned in `pyproject.toml`.
