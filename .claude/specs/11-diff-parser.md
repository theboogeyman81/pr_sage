# Feature 11: diff-parser

## Goal
Parse a raw unified diff string into a structured list of per-file diffs, each containing hunks with old/new line ranges and the raw diff lines.

## In scope
- `app/parser/diff.py` — `Range`, `Hunk`, `FileDiff` dataclasses + `parse_diff(raw: str) -> list[FileDiff]`
- `tests/fixtures/sample.diff` — fixture diff covering modified, added, and deleted files plus unsupported cases
- `tests/test_diff_parser.py` — 5 tests
- No new dependencies — stdlib only (`re`, `dataclasses`)

## Out of scope
- Binary diffs — skip cleanly (produce no `FileDiff` for that file)
- Rename-only diffs (no content change) — skip cleanly
- Renames with content — skip cleanly (treat as unsupported)
- Non-git unified diffs (no `diff --git` header)

## File structure
```
app/
  parser/
    __init__.py   # exists
    diff.py       # new — dataclasses + parse_diff()
tests/
  fixtures/
    sample.diff   # new — fixture diff
  test_diff_parser.py  # new — 5 tests
```

## Contracts

### `app/parser/diff.py`

```python
from dataclasses import dataclass, field

@dataclass
class Range:
    start: int   # 1-indexed line number
    count: int   # number of lines (0 for empty files)

@dataclass
class Hunk:
    old_range: Range
    new_range: Range
    lines: list[str]   # each line includes its leading prefix: ' ', '+', or '-'

@dataclass
class FileDiff:
    path: str          # new file path; old path if file was deleted
    hunks: list[Hunk] = field(default_factory=list)
```

```python
def parse_diff(raw: str) -> list[FileDiff]:
    """
    Parse a unified diff (as returned by GitHub's diff API) into FileDiff objects.

    Skips binary diffs and rename-only/rename-with-content entries silently.
    Returns an empty list for an empty or unrecognised input.
    """
```

**Parsing strategy (all stdlib, no external deps):**
1. Split on `diff --git ` to get per-file sections.
2. For each section:
   - If `Binary files` appears → skip.
   - If `rename from` appears → skip.
   - Extract path from `+++ b/<path>` line. If `+++ /dev/null` → use `--- a/<path>` (deleted file).
   - Find all hunk headers matching `@@ -old_start[,old_count] +new_start[,new_count] @@`.
   - `count` defaults to `1` when omitted in the `@@` header.
   - Collect lines for each hunk until the next `@@` or `diff --git`.
3. Skip sections where no `+++` line is found (malformed or unsupported).

### `tests/fixtures/sample.diff`

```
diff --git a/app/foo.py b/app/foo.py
index abc1234..def5678 100644
--- a/app/foo.py
+++ b/app/foo.py
@@ -1,4 +1,5 @@
 import os
+import sys
 
 def main():
-    pass
+    print("hello")
diff --git a/app/new_file.py b/app/new_file.py
new file mode 100644
index 0000000..1111111
--- /dev/null
+++ b/app/new_file.py
@@ -0,0 +1,3 @@
+def greet():
+    return "hi"
+
diff --git a/app/deleted.py b/app/deleted.py
deleted file mode 100644
index 2222222..0000000
--- a/app/deleted.py
+++ /dev/null
@@ -1,2 +0,0 @@
-def old():
-    pass
diff --git a/assets/image.png b/assets/image.png
index 3333333..4444444 100644
Binary files a/assets/image.png and b/assets/image.png differ
diff --git a/app/renamed.py b/app/renamed_new.py
similarity index 100%
rename from app/renamed.py
rename to app/renamed_new.py
```

## Dependencies
None — stdlib only.

## Tests

```python
# tests/test_diff_parser.py
from pathlib import Path
from app.parser.diff import parse_diff, FileDiff, Hunk, Range

RAW = (Path(__file__).parent / "fixtures" / "sample.diff").read_text()
RESULTS = parse_diff(RAW)
BY_PATH = {f.path: f for f in RESULTS}
```

- `test_parsed_file_count` — `len(RESULTS) == 3` (modified + new + deleted; binary and rename skipped).
- `test_modified_file_hunk` — `"app/foo.py"` has 1 hunk; `old_range == Range(1, 4)`; `new_range == Range(1, 5)`; lines list contains `"+import sys"`.
- `test_new_file_path_and_range` — `"app/new_file.py"` present; hunk `old_range == Range(0, 0)`; `new_range == Range(1, 3)`.
- `test_deleted_file_path` — `"app/deleted.py"` present (path from `--- a/` since `+++ /dev/null`).
- `test_binary_and_rename_skipped` — `"assets/image.png"` and `"app/renamed_new.py"` are NOT in `BY_PATH`.

## Acceptance criteria
1. All 5 tests pass.
2. Binary diffs and rename-only diffs produce no `FileDiff` — no crash, no entry.
3. `@@ -0,0 +1,3 @@` (new file) parsed correctly: `old_range.start=0, old_range.count=0`.
4. Deleted file uses old path (`--- a/<path>`) when `+++ /dev/null`.
5. Each line in `Hunk.lines` preserves its leading ` `, `+`, or `-` prefix.
6. All existing 23 tests remain green.
