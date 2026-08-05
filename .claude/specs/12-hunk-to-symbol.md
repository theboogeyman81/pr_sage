# Feature 12: hunk-to-symbol

## Goal
Given a `Hunk` and a file's parsed `Symbol` list, return every `Symbol` whose line range overlaps the hunk's new-file line range.

## In scope
- `app/parser/hunk.py` — `symbols_touched(hunk: Hunk, symbols: list[Symbol]) -> list[Symbol]`
- `tests/test_hunk_to_symbol.py` — 6 tests (5 placement cases + pure-deletion edge case)
- No new dependencies — imports only from F10 (`Symbol`) and F11 (`Hunk`, `Range`)

## Out of scope
- Cross-file symbol resolution
- Call-graph analysis (callers/callees)
- Modifying `parse_python` or `parse_diff`
- Handling old-file line numbers (old_range is ignored)

## File structure
```
app/
  parser/
    hunk.py               # new — symbols_touched()
tests/
  test_hunk_to_symbol.py  # new — 6 tests
```

## Contracts

### `app/parser/hunk.py`

```python
from app.parser.diff import Hunk
from app.parser.python import Symbol

def symbols_touched(hunk: Hunk, symbols: list[Symbol]) -> list[Symbol]:
    """
    Return every Symbol whose line range overlaps hunk.new_range.

    Uses new_range (lines in the new file). Pure-deletion hunks
    (new_range.count == 0) always return []. Symbols are returned
    in the same order as the input list.
    """
```

**Algorithm:**
- `hunk_start = hunk.new_range.start`
- `hunk_end = hunk.new_range.start + hunk.new_range.count - 1`
- If `hunk_end < hunk_start` (i.e. `count == 0`) → return `[]`
- A symbol overlaps if: `symbol.start_line <= hunk_end AND symbol.end_line >= hunk_start`
- Return all matching symbols in input order

**Why `new_range`:** Symbols are parsed from the new file source; `new_range` gives the corresponding line coordinates. There are no new lines to annotate in a pure-deletion hunk, so those return `[]`.

## Tests

Symbols are constructed inline (no fixture file). Shared fixture:

```
top_func   — kind="function", start=1,  end=5
mid_class  — kind="class",    start=7,  end=20
method_one — kind="function", start=9,  end=13
method_two — kind="function", start=15, end=19
bot_func   — kind="function", start=22, end=25
```

All tests call `symbols_touched(hunk, SYMBOLS)` where `SYMBOLS = [top_func, mid_class, method_one, method_two, bot_func]`.

| Test | new_range | Expected result | Criterion covered |
|------|-----------|-----------------|-------------------|
| `test_inside_one_symbol` | Range(2, 2) → lines 2–3 | `[top_func]` | inside |
| `test_crossing_two_symbols` | Range(4, 5) → lines 4–8 | `[top_func, mid_class]` | crossing |
| `test_at_boundary` | Range(5, 1) → line 5 | `[top_func]` | at boundary (top_func.end_line == 5) |
| `test_outside_all_symbols` | Range(6, 1) → line 6 | `[]` | outside (gap between top_func and mid_class) |
| `test_inside_method_of_class` | Range(10, 2) → lines 10–11 | `[mid_class, method_one]` | inside nested (method_one is inside mid_class; both ranges overlap) |
| `test_pure_deletion_hunk` | Range(5, 0) → count=0 | `[]` | deletion edge case |

## Dependencies
None — stdlib only, no new packages.

## Acceptance criteria
1. All 6 tests pass.
2. Hunk entirely inside one symbol → only that symbol returned.
3. Hunk crossing a boundary → both symbols returned.
4. Hunk at exact start or end line of a symbol → that symbol returned (inclusive).
5. Hunk in a gap between symbols → empty list.
6. Hunk inside a method whose class also overlaps → both class and method returned, in source order.
7. Pure-deletion hunk (`new_range.count == 0`) → empty list.
8. All existing 28 tests remain green.
