from unittest.mock import MagicMock, patch

import pytest

from app.analysis.finding import RuffError
from app.analysis.ruff_runner import run_ruff

_CLEAN = "x = 1\n"
_UNUSED_IMPORT = "import os\n"


def test_clean_file_returns_no_findings():
    result = run_ruff({"app/foo.py": _CLEAN})
    assert result == []


def test_unused_import_found():
    findings = run_ruff({"app/foo.py": _UNUSED_IMPORT})
    assert len(findings) >= 1
    f = findings[0]
    assert f.rule == "F401"
    assert f.path == "app/foo.py"
    assert f.line >= 1


def test_multiple_files():
    findings = run_ruff({"app/clean.py": _CLEAN, "app/bad.py": _UNUSED_IMPORT})
    paths = {f.path for f in findings}
    assert "app/bad.py" in paths
    assert "app/clean.py" not in paths


def test_path_key_preserved():
    findings = run_ruff({"my/custom/path.py": _UNUSED_IMPORT})
    assert all(f.path == "my/custom/path.py" for f in findings)
    assert all("/tmp" not in f.path for f in findings)


def test_ruff_error_raises():
    mock_result = MagicMock()
    mock_result.returncode = 2
    mock_result.stderr = "ruff internal error"
    mock_result.stdout = ""
    with patch("subprocess.run", return_value=mock_result):
        with pytest.raises(RuffError):
            run_ruff({"app/foo.py": _CLEAN})
