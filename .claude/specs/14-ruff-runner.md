# Feature 14: Ruff Runner

## Goal
Run ruff on a dict of `{path: source}` strings and return structured findings, using a temp directory so ruff sees real files with their original paths preserved.

## In scope
- `Finding` dataclass defined in `app/analysis/finding.py` — shared schema for F14, F15, F16.
- `run_ruff(files: dict[str, str]) -> list[Finding]` in `app/analysis/ruff_runner.py`.
- Invokes `ruff check --output-format json --no-cache` via `subprocess.run` on a temp directory.
- Preserves original path keys in returned findings (not the temp dir path).
- Returns `[]` (not raises) when ruff exits non-zero due to lint findings (exit code 1 is normal).
- Raises `RuffError` (new exception) only when ruff itself fails to run (exit code 2+, binary missing, etc.).
- Tests with two fixture source strings: one clean file (no findings) and one that trips known rules.

## Out of scope
- Configurable rule sets (Phase 6 / F21).
- Auto-fix mode.
- Running ruff on files already on disk (always takes source strings).
- mypy (F15).

## File structure
```
app/
  analysis/
    __init__.py          ← new (empty)
    finding.py           ← new: Finding dataclass + RuffError
    ruff_runner.py       ← new: run_ruff()
tests/
  test_ruff_runner.py    ← new
pyproject.toml           ← add ruff==0.16.1 to dependencies
.claude/
  specs/14-ruff-runner.md
```

## Contracts

```python
# app/analysis/finding.py

from dataclasses import dataclass

@dataclass(frozen=True)
class Finding:
    path: str     # original path key from the input dict
    line: int     # 1-indexed
    col: int      # 1-indexed
    rule: str     # e.g. "F401", "E501"
    message: str  # human-readable ruff message


class RuffError(Exception):
    """Raised when ruff itself fails (exit code ≥ 2, binary not found, etc.)."""
```

```python
# app/analysis/ruff_runner.py

def run_ruff(files: dict[str, str]) -> list[Finding]:
    """
    Write each source string to a temp dir, run ruff, return findings
    with paths mapped back to the original dict keys.
    Returns [] for clean files. Raises RuffError on ruff execution failure.
    """
```

Ruff invocation:
```
ruff check --output-format json --no-cache <file1> <file2> ...
```
Exit codes: 0 = no findings, 1 = findings found (both are success), ≥2 = ruff error.

Ruff JSON output shape per finding (fields we use):
```json
{
  "filename": "/tmp/xxx/app/foo.py",
  "message": "...",
  "code": "F401",
  "location": {"row": 3, "column": 1}
}
```

## Dependencies
- `ruff==0.16.1` — add to `[project].dependencies` in `pyproject.toml`

## Tests
- `test_clean_file_returns_no_findings`: source with no lint issues → `[]`
- `test_unused_import_found`: source with `import os` (unused) → finding with `rule="F401"`, correct `path`, `line ≥ 1`
- `test_multiple_files`: two files passed, only the bad one produces findings; clean file absent from results
- `test_path_key_preserved`: finding's `path` matches the original dict key, not the temp dir path
- `test_ruff_error_raises`: patch `subprocess.run` to return exit code 2 → `RuffError` raised

## Acceptance criteria
1. `run_ruff({"app/foo.py": "import os\n"})` returns at least one `Finding` with `rule="F401"` and `path="app/foo.py"`.
2. `run_ruff({"app/foo.py": "x = 1\n"})` returns `[]`.
3. All 5 tests pass with `pytest`.
4. `ruff==0.16.1` pinned in `pyproject.toml`.
5. `Finding.path` always matches the input dict key, never a temp path.
