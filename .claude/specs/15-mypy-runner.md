# Feature 15: Mypy Runner

## Goal
Run mypy on a dict of `{path: source}` strings and return structured `Finding` objects, handling missing type stubs gracefully, using the same temp-dir pattern as `run_ruff`.

## In scope
- Add `severity: str = "error"` field to `Finding` in `app/analysis/finding.py` (backward-compatible default; ruff findings all use `"error"`).
- Update `run_ruff` in `app/analysis/ruff_runner.py` to pass `severity="error"` explicitly (no behavior change, just makes the field set explicitly).
- `MypyError` exception added to `app/analysis/finding.py`.
- `run_mypy(files: dict[str, str]) -> list[Finding]` in `app/analysis/mypy_runner.py`.
- Invokes `mypy --output json --ignore-missing-imports --no-error-summary` via `subprocess.run` on a temp directory.
- Parses mypy's NDJSON output (one JSON object per line).
- Filters out `severity="note"` lines — only `"error"` and `"warning"` become `Finding` objects.
- Returns `[]` (not raises) when mypy exits 0 or 1 (type errors are normal). Raises `MypyError` on exit code ≥ 2.
- Tests with fixture sources: one clean file, one with a type error, one with a missing import (must not crash).

## Out of scope
- Whole-repo type checking (only checks files passed in).
- Configurable mypy settings (Phase 6 / F21).
- `run_ruff` behavior changes beyond adding `severity="error"` explicitly.

## File structure
```
app/
  analysis/
    finding.py        ← modified: add severity field + MypyError
    ruff_runner.py    ← modified: pass severity="error" explicitly
    mypy_runner.py    ← new: run_mypy()
tests/
  test_mypy_runner.py ← new
pyproject.toml        ← add mypy==1.16.1 to dependencies
.claude/
  specs/15-mypy-runner.md
```

## Contracts

```python
# app/analysis/finding.py (updated)

@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    col: int
    rule: str       # ruff: e.g. "F401" | mypy: e.g. "attr-defined", "return-value"
    message: str
    severity: str = "error"   # "error" | "warning" | "note" (notes filtered out by run_mypy)


class MypyError(Exception):
    """Raised when mypy exits with code ≥ 2 (fatal error, bad options, etc.)."""
```

```python
# app/analysis/mypy_runner.py

def run_mypy(files: dict[str, str]) -> list[Finding]:
    """
    Write each source string to a temp dir, run mypy, return findings.
    Notes (severity="note") are silently dropped.
    Returns [] for clean files. Raises MypyError on mypy execution failure.
    """
```

Mypy invocation:
```
mypy --output json --ignore-missing-imports --no-error-summary <file1> <file2> ...
```

Mypy NDJSON output shape per line (fields we use):
```json
{"file": "/tmp/xxx/app/foo.py", "line": 3, "column": 0, "message": "...", "code": "return-value", "severity": "error"}
```

Exit codes: 0 = no errors, 1 = type errors found (both normal), ≥ 2 = fatal mypy error.

## Dependencies
- `mypy==1.16.1` — add to `[project].dependencies` in `pyproject.toml`

## Tests
- `test_clean_file_returns_no_findings`: well-typed source → `[]`
- `test_type_error_found`: source with a clear type error (e.g. `def f() -> int: return "x"`) → finding with `rule` set and `severity="error"`, correct `path`
- `test_missing_import_does_not_crash`: source with `import nonexistent_pkg` → does not raise, returns `[]` (stubs missing, `--ignore-missing-imports` suppresses)
- `test_path_key_preserved`: finding `path` matches original dict key, not a temp path
- `test_mypy_error_raises`: patch `subprocess.run` to return exit code 2 → `MypyError` raised

## Acceptance criteria
1. `run_mypy({"app/foo.py": "def f() -> int:\n    return 'x'\n"})` returns at least one `Finding` with `severity="error"` and `path="app/foo.py"`.
2. `run_mypy({"app/foo.py": "import nonexistent_pkg\n"})` returns `[]` without raising.
3. All 5 tests pass with `pytest`.
4. `mypy==1.16.1` pinned in `pyproject.toml`.
5. Full test suite (44 existing + 5 new) still green — `severity` default ensures no ruff test breakage.
