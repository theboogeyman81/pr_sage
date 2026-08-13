from unittest.mock import MagicMock, patch

import pytest

from app.github.context import ContextExpander
from app.github.exceptions import FileNotFoundAtSHA
from app.parser.python import Symbol

_SHA = "a" * 40
_REPO = "owner/repo"
_PATH = "app/foo.py"
_INSTALL_ID = 42

_FILE_LINES = [f"line_{i:02d}" for i in range(1, 21)]  # 20 lines: line_01 … line_20
_FILE_TEXT = "\n".join(_FILE_LINES)


def _fake_response(status_code: int = 200, text: str = _FILE_TEXT) -> MagicMock:
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


@pytest.fixture
def expander(auth_mock):
    return ContextExpander(auth=auth_mock)


def _symbol(start: int, end: int) -> Symbol:
    return Symbol(name="fn", kind="function", start_line=start, end_line=end)


def test_expand_context_fetches_and_slices(expander):
    # Symbol at lines 8–12, padding=3 → expect lines 5–15 (0-indexed 4–14)
    with patch("httpx.get", return_value=_fake_response()):
        result = expander.expand_context(_REPO, _SHA, _PATH, _symbol(8, 12), _INSTALL_ID, padding=3)

    expected = "\n".join(_FILE_LINES[4:15])
    assert result == expected


def test_expand_context_cache_hit(expander):
    with patch("httpx.get", return_value=_fake_response()) as mock_get:
        expander.expand_context(_REPO, _SHA, _PATH, _symbol(1, 5), _INSTALL_ID)
        expander.expand_context(_REPO, _SHA, _PATH, _symbol(6, 10), _INSTALL_ID)

    mock_get.assert_called_once()


def test_expand_context_cache_miss_different_sha(expander):
    sha2 = "b" * 40
    with patch("httpx.get", return_value=_fake_response()) as mock_get:
        expander.expand_context(_REPO, _SHA, _PATH, _symbol(1, 5), _INSTALL_ID)
        expander.expand_context(_REPO, sha2, _PATH, _symbol(1, 5), _INSTALL_ID)

    assert mock_get.call_count == 2


def test_expand_context_404_raises(expander):
    with patch("httpx.get", return_value=_fake_response(status_code=404)):
        with pytest.raises(FileNotFoundAtSHA):
            expander.expand_context(_REPO, _SHA, _PATH, _symbol(1, 5), _INSTALL_ID)


def test_expand_context_padding_clamped(expander):
    # Symbol at line 2, padding=10 — start must clamp to 0, no IndexError
    with patch("httpx.get", return_value=_fake_response()):
        result = expander.expand_context(_REPO, _SHA, _PATH, _symbol(2, 2), _INSTALL_ID, padding=10)

    # start clamped to 0, end = min(20, 2+10) = 12
    expected = "\n".join(_FILE_LINES[0:12])
    assert result == expected
