import time
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import jwt
import pytest

from app.github.auth import GitHubAppAuth


@pytest.fixture(scope="module")
def rsa_key_pem():
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    )
    return pem.decode()


@pytest.fixture
def auth(rsa_key_pem):
    return GitHubAppAuth(app_id="12345", private_key=rsa_key_pem)


def _fake_response(minutes_from_now: int = 60) -> MagicMock:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=minutes_from_now)
    mock = MagicMock()
    mock.json.return_value = {
        "token": "tok_abc",
        "expires_at": expires_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    mock.raise_for_status = MagicMock()
    return mock


def test_make_jwt_claims(auth):
    before = int(time.time())
    token = auth._make_jwt()
    decoded = jwt.decode(token, options={"verify_signature": False})
    after = int(time.time())

    assert decoded["iss"] == "12345"
    assert before <= decoded["iat"] <= after
    assert decoded["exp"] - decoded["iat"] == 600


def test_get_installation_token_calls_github(auth):
    with patch("httpx.post", return_value=_fake_response()) as mock_post:
        token = auth.get_installation_token(42)

    assert token == "tok_abc"
    assert mock_post.call_count == 1


def test_get_installation_token_cache_hit(auth):
    with patch("httpx.post", return_value=_fake_response()) as mock_post:
        auth.get_installation_token(99)
        auth.get_installation_token(99)

    assert mock_post.call_count == 1


def test_get_installation_token_cache_miss_after_expiry(auth):
    with patch("httpx.post", return_value=_fake_response(minutes_from_now=3)) as mock_post:
        auth.get_installation_token(77)
        auth.get_installation_token(77)

    assert mock_post.call_count == 2
