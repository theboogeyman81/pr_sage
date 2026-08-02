from unittest.mock import MagicMock, patch

import pytest

from app.github.diff import fetch_pr_diff
from app.github.exceptions import GitHubServerError, PRAccessDeniedError, PRNotFoundError

_DIFF_TEXT = "--- a/foo.py\n+++ b/foo.py\n@@ -1,1 +1,2 @@\n+x = 1\n"


def _fake_get(status_code: int = 200, text: str = _DIFF_TEXT) -> MagicMock:
    mock = MagicMock()
    mock.status_code = status_code
    mock.text = text
    mock.raise_for_status = MagicMock()
    return mock


@pytest.fixture
def auth_mock():
    mock = MagicMock()
    mock.get_installation_token.return_value = "tok_test"
    return mock


def test_fetch_pr_diff_success(auth_mock):
    with patch("httpx.get", return_value=_fake_get()) as mock_get:
        result = fetch_pr_diff("owner/repo", 7, 42, auth=auth_mock)

    assert result == _DIFF_TEXT
    auth_mock.get_installation_token.assert_called_once_with(42)
    call_kwargs = mock_get.call_args
    assert "repos/owner/repo/pulls/7" in call_kwargs.args[0]
    assert call_kwargs.kwargs["headers"]["Accept"] == "application/vnd.github.v3.diff"


def test_fetch_pr_diff_404(auth_mock):
    with patch("httpx.get", return_value=_fake_get(status_code=404)):
        with pytest.raises(PRNotFoundError):
            fetch_pr_diff("owner/repo", 7, 42, auth=auth_mock)


def test_fetch_pr_diff_403(auth_mock):
    with patch("httpx.get", return_value=_fake_get(status_code=403)):
        with pytest.raises(PRAccessDeniedError):
            fetch_pr_diff("owner/repo", 7, 42, auth=auth_mock)


def test_fetch_pr_diff_5xx(auth_mock):
    with patch("httpx.get", return_value=_fake_get(status_code=500)):
        with pytest.raises(GitHubServerError):
            fetch_pr_diff("owner/repo", 7, 42, auth=auth_mock)
