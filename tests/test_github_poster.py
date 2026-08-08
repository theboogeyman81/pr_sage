from unittest.mock import MagicMock, patch

import pytest

from app.github.auth import GitHubAppAuth
from app.github.exceptions import GitHubServerError, PRAccessDeniedError, PRNotFoundError
from app.github.poster import post_review
from app.llm.review_agent import Comment

_REPO = "owner/repo"
_PR = 42
_INSTALL = 99
_COMMENT = Comment(path="app/foo.py", line=5, body="fix this", severity="error")


def _mock_auth() -> GitHubAppAuth:
    auth = MagicMock(spec=GitHubAppAuth)
    auth.get_installation_token.return_value = "tok"
    return auth


def _mock_response(status_code: int) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.raise_for_status.return_value = None
    return resp


@pytest.fixture()
def auth():
    return _mock_auth()


def test_post_review_success(auth):
    with patch("app.github.poster.httpx.post", return_value=_mock_response(200)) as mock_post:
        post_review(_REPO, _PR, _INSTALL, [_COMMENT], auth=auth)
    mock_post.assert_called_once()
    url = mock_post.call_args[0][0]
    assert url == f"https://api.github.com/repos/{_REPO}/pulls/{_PR}/reviews"


def test_post_review_empty_no_op(auth):
    with patch("app.github.poster.httpx.post") as mock_post:
        post_review(_REPO, _PR, _INSTALL, [], auth=auth)
    mock_post.assert_not_called()


def test_post_review_body_severity_prefix(auth):
    with patch("app.github.poster.httpx.post", return_value=_mock_response(200)) as mock_post:
        post_review(_REPO, _PR, _INSTALL, [_COMMENT], auth=auth)
    payload = mock_post.call_args.kwargs["json"]
    assert payload["comments"][0]["body"].startswith("[error]")


def test_post_review_404_raises(auth):
    with patch("app.github.poster.httpx.post", return_value=_mock_response(404)):
        with pytest.raises(PRNotFoundError):
            post_review(_REPO, _PR, _INSTALL, [_COMMENT], auth=auth)


def test_post_review_403_raises(auth):
    with patch("app.github.poster.httpx.post", return_value=_mock_response(403)):
        with pytest.raises(PRAccessDeniedError):
            post_review(_REPO, _PR, _INSTALL, [_COMMENT], auth=auth)


def test_post_review_500_raises(auth):
    with patch("app.github.poster.httpx.post", return_value=_mock_response(500)):
        with pytest.raises(GitHubServerError):
            post_review(_REPO, _PR, _INSTALL, [_COMMENT], auth=auth)
