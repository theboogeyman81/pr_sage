# Feature 16: Analysis Aggregator

## Goal
Given a combined list of ruff + mypy findings and a parsed diff, return only the findings whose line falls on an added (`+`) line in the diff.

## In scope
- `aggregate(findings: list[Finding], diff: list[FileDiff]) -> list[Finding]` in `app/analysis/aggregator.py`.
- Helper `_added_lines(diff: list[FileDiff]) -> dict[str, set[int]]` — builds a `{path: {line_numbers}}` map of all `+` lines across all hunks.
- Walking hunk lines to compute new-file line numbers: context lines (` `) and added lines (`+`) advance the new-file counter; removed lines (`-`) do not.
- Findings for files not present in the diff are dropped entirely.
- Findings on context or removed lines (not `+`) are dropped.
- Out of scope: dedup across tools (a ruff and mypy finding on the same line both survive).

## Out of scope
- Deduplication across tools.
- Modifying or enriching findings (pass-through only).
- Any awareness of severity or rule — all findings are treated equally.

## File structure
```
app/
  analysis/
    aggregator.py        ← new: aggregate() + _added_lines()
tests/
  test_aggregator.py     ← new
.claude/
  specs/16-analysis-aggregator.md
```

No new dependencies. No `pyproject.toml` changes.

## Contracts

```python
# app/analysis/aggregator.py

from app.analysis.finding import Finding
from app.parser.diff import FileDiff

def aggregate(findings: list[Finding], diff: list[FileDiff]) -> list[Finding]:
    """Return findings that land on a '+' line in the diff."""

def _added_lines(diff: list[FileDiff]) -> dict[str, set[int]]:
    """Build {path: {new_file_line_numbers}} for all '+' lines in the diff."""
```

### Line-number walking logic for `_added_lines`

For each `FileDiff` → each `Hunk`:
- `new_lineno = hunk.new_range.start`
- For each `line` in `hunk.lines`:
  - `+` prefix → this line is at `new_lineno`; add to set; `new_lineno += 1`
  - ` ` prefix (context) → `new_lineno += 1`
  - `-` prefix → do not increment `new_lineno`

## Tests

Fixture diff used across tests (single file `app/foo.py`, one hunk):
```
@@ -10,4 +10,6 @@
  context_before
-removed_line
+added_line_1
+added_line_2
  context_after
```
Added lines in new file: 11, 12. Context lines: 10, 13. Removed line: not in new file.

- `test_finding_on_added_line_kept`: finding at `line=11` on `app/foo.py` → returned
- `test_finding_on_context_line_dropped`: finding at `line=10` (context) → dropped
- `test_finding_on_removed_line_dropped`: finding at old line (not a new-file line) → dropped
- `test_finding_for_unknown_file_dropped`: finding on a file not in diff → dropped
- `test_multiple_findings_mixed`: three findings on same file — one on `+` line, one on context, one on unknown file → only the `+` one returned
- `test_empty_findings_returns_empty`: `aggregate([], diff)` → `[]`
- `test_empty_diff_drops_all`: `aggregate([finding], [])` → `[]`

## Acceptance criteria
1. `aggregate` returns only findings whose `(path, line)` maps to a `+` line in the diff.
2. Findings for files absent from the diff are dropped.
3. All 7 tests pass with `pytest`.
4. No new dependencies added.
5. Full suite (49 existing + 7 new) stays green.
