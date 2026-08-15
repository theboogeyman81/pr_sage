# Feature 25: Eval Dataset Schema

## Goal
Define a JSONL format for labeled PR review examples so F26's eval runner has
a stable, validated input contract to score the review agent against.

## In scope
- `app/eval/schema.py` — Pydantic models (`ExpectedFinding`, `EvalExample`) +
  `load_dataset(path: Path) -> list[EvalExample]` loader with line-level error
  reporting
- `eval_data/seed.jsonl` — seed dataset; **Pratham labels these by hand before
  F26 starts** (at least 5 examples required for the acceptance criteria)
- `tests/test_eval_schema.py` — 6 tests over the loader and models

## Out of scope
- Eval scoring / precision-recall logic (F26)
- LLM-generated labels
- Per-repo dataset splits

## File structure
```
app/
    eval/
        __init__.py        ← empty
        schema.py          ← new
eval_data/
    seed.jsonl             ← new (Pratham fills in real examples)
tests/
    test_eval_schema.py    ← new
```

## Contracts

### JSONL record shape
One JSON object per line. Blank lines ignored.

```json
{
  "diff":     "<unified diff string>",
  "context":  "<expanded symbol source, may be empty string>",
  "expected_findings": [
    {
      "path":       "app/foo.py",
      "line_range": [10, 15],
      "category":   "bare-except"
    }
  ],
  "notes": "optional human annotation or empty string"
}
```

Field rules:
- `diff` — required, non-empty string
- `context` — required, string (may be `""` if no context was captured)
- `expected_findings` — required, list; may be empty `[]` (example of a clean diff)
- `expected_findings[].path` — required, non-empty string
- `expected_findings[].line_range` — required, exactly 2 positive ints `[start, end]`,
  `start <= end`, both 1-indexed
- `expected_findings[].category` — required, non-empty free-form string
  (e.g. `"bare-except"`, `"missing-type-annotation"`, `"logic-error"`)
- `notes` — optional string; defaults to `""` if absent

### `app/eval/schema.py`
```python
from pathlib import Path
from pydantic import BaseModel, field_validator

class ExpectedFinding(BaseModel):
    path: str
    line_range: tuple[int, int]
    category: str

    @field_validator("line_range")
    @classmethod
    def _validate_range(cls, v):
        # start >= 1, end >= start
        ...

class EvalExample(BaseModel):
    diff: str
    context: str
    expected_findings: list[ExpectedFinding]
    notes: str = ""

class EvalDatasetError(Exception):
    """Raised when a JSONL line fails to parse or validate, with line number."""

def load_dataset(path: Path) -> list[EvalExample]:
    """Read path as JSONL; raises EvalDatasetError on first invalid line."""
    ...
```

## Dependencies
No new packages. Pydantic is already available via `pydantic-settings==2.7.0`.

## Tests
All tests use inline JSONL strings written to a `tmp_path` fixture file —
no dependency on `eval_data/seed.jsonl`.

- `test_valid_example_parses` — full valid record → `EvalExample` with correct fields
- `test_empty_findings_valid` — `expected_findings: []` → loads without error
- `test_notes_defaults_to_empty_string` — record without `notes` key →
  `example.notes == ""`
- `test_missing_diff_raises` — record without `diff` → `EvalDatasetError`
- `test_invalid_line_range_raises` — `line_range: [5, 3]` (start > end) →
  `EvalDatasetError`
- `test_loader_reads_multiple_lines` — 3-line JSONL → `list` of 3 `EvalExample`

## Acceptance criteria
1. `load_dataset` successfully parses any valid JSONL file, returning one
   `EvalExample` per non-blank line
2. `load_dataset` raises `EvalDatasetError` (not a raw `ValidationError`) on any
   invalid line, with the line number in the error message
3. `expected_findings` may be an empty list (clean-diff examples are valid)
4. `line_range` with `start > end` or any value < 1 is rejected at load time
5. `pytest tests/test_eval_schema.py -v` → 6 tests pass
6. `pytest tests/ -v` → all 103 existing tests pass
7. `eval_data/seed.jsonl` exists and contains ≥ 5 valid examples
   (Pratham provides these before F26 begins)
