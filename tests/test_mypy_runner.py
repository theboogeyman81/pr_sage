from unittest.mock import MagicMock, patch

import pytest

from app.analysis.finding import MypyError
from app.analysis.mypy_runner import run_mypy

_CLEAN = "x: int = 1\n"
_TYPE_ERROR = "def f() -> int:\n    return 'x'\n"
_MISSING_IMPORT = "import nonexistent_pkg\n"


def test_clean_file_returns_no_findings():
    result = run_mypy({"app/foo.py": _CLEAN})
    assert result == []


def test_type_error_found():
    findings = run_mypy({"app/foo.py": _TYPE_ERROR})
    assert len(findings) >= 1
    f = findings[0]
    assert f.severity == "error"
    assert f.path == "app/foo.py"
    assert f.line >= 1
    assert f.rule  # non-empty rule code


def test_missing_import_does_not_crash():
    result = run_mypy({"app/foo.py": _MISSING_IMPORT})
    assert isinstance(result, list)


def test_path_key_preserved():
    findings = run_mypy({"my/custom/path.py": _TYPE_ERROR})
    assert all(f.path == "my/custom/path.py" for f in findings)
    assert all("/tmp" not in f.path and "\\Temp" not in f.path for f in findings)


def test_mypy_error_raises():
    mock_result = MagicMock()
    mock_result.returncode = 2
    mock_result.stderr = "mypy fatal error"
    mock_result.stdout = ""
    with patch("subprocess.run", return_value=mock_result):
        with pytest.raises(MypyError):
            run_mypy({"app/foo.py": _CLEAN})
