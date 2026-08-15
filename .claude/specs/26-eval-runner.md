# Feature 26: Eval Runner

## Goal
Run the review agent against the labeled dataset and produce a scored report
so Pratham can compare prompt/model changes across runs.

## Roles (per CLAUDE.md §3)
- **Pratham implements** the body of `score()` in `app/eval/scorer.py` —
  the precision/recall matching logic and category grouping.
- **Claude Code builds** everything else: the runner scaffolding, cost
  accumulator, report serialization, CLI, and tests (mocking the scorer).

## In scope
- `app/eval/scorer.py` — `CategoryResult` dataclass + `score()` stub
  (Pratham fills in the body)
- `app/eval/runner.py` — `run_eval()` orchestrator + `__main__` CLI entry
- `app/eval/_cost.py` — `_CostAccumulator` wrapper that intercepts
  `GeminiClient.complete()` calls to sum token usage without modifying
  existing interfaces
- Report format: `eval_reports/<timestamp>_<model>.json`
- Tests in `tests/test_eval_runner.py`

## Out of scope
- LLM-judge scoring
- CI integration (F27)
- Cross-run diff tooling
- Running ruff/mypy on examples (pass `findings=[]` to `run_review`)

## File structure
```
app/
    eval/
        _cost.py           ← new
        scorer.py          ← new (stub; Pratham implements score())
        runner.py          ← new
eval_reports/
    .gitkeep               ← new (directory tracked, reports gitignored)
tests/
    test_eval_runner.py    ← new
```

## Contracts

### `app/eval/scorer.py`
```python
from dataclasses import dataclass
from app.eval.schema import ExpectedFinding
from app.llm.review_agent import Comment

@dataclass
class CategoryResult:
    tp: int       # expected findings matched by an agent comment
    fp: int       # agent comments with no matching expected finding
    fn: int       # expected findings with no matching agent comment
    precision: float   # tp / (tp + fp), or 1.0 if tp+fp == 0
    recall: float      # tp / (tp + fn), or 1.0 if tp+fn == 0

def score(
    expected: list[ExpectedFinding],
    actual: list[Comment],
) -> dict[str, CategoryResult]:
    """
    Match Comments to ExpectedFindings and return per-category results.

    Matching rule (Pratham implements):
      A Comment matches an ExpectedFinding if:
        1. comment.path == expected.path
        2. expected.line_range[0] <= comment.line <= expected.line_range[1]
      Each expected finding may match at most one comment (greedy, first match).
      FP = unmatched comments (no expected finding covers their location).
      Results are keyed by expected finding category; unmatched comments
      contribute to a special "_unmatched" category or are counted globally.
    """
    raise NotImplementedError("Pratham implements this in F26")
```

### `app/eval/_cost.py`
Duck-typed wrapper — passes through to inner `GeminiClient.complete()` while
accumulating token counts. Works with `run_review()` since that function only
calls `client.complete()`.

```python
class _CostAccumulator:
    def __init__(self, inner: GeminiClient) -> None: ...
    def complete(self, messages, *, model, max_tokens, system=None) -> GeminiResponse: ...
    def total_cost_usd(self, model: str) -> float | None:
        # uses estimate_cost() from app.llm.cost_table
        ...
```

### `app/eval/runner.py`

```python
def run_eval(
    dataset_path: Path,
    *,
    model: str,
    prompt_version: int,
    output_dir: Path,
) -> Path:
    """
    Load dataset, run review agent on each example, score, write report.
    Returns path to the written report file.
    Skips examples where run_review raises ReviewError (logged as warnings).
    """
    ...
```

### Report JSON shape
Written to `eval_reports/<ISO-timestamp>_<model>.json`:
```json
{
  "timestamp": "2026-08-11T10:00:00Z",
  "model": "gemini-2.0-flash",
  "prompt_version": 2,
  "dataset": "eval_data/seed.jsonl",
  "total_examples": 5,
  "skipped_examples": 0,
  "total_cost_usd": 0.0031,
  "by_category": {
    "bare-except": {"tp": 3, "fp": 0, "fn": 1, "precision": 1.0, "recall": 0.75},
    "missing-type-annotation": {"tp": 1, "fp": 1, "fn": 0, "precision": 0.5, "recall": 1.0}
  },
  "overall": {"precision": 0.8, "recall": 0.85}
}
```

### CLI
```
python -m app.eval.runner \
    --dataset eval_data/seed.jsonl \
    --model gemini-2.0-flash \
    --prompt-version 2 \
    --output-dir eval_reports/
```

## Dependencies
No new packages. Uses `argparse`, `datetime`, `json` (stdlib) and existing
`app.eval.schema`, `app.llm.{gemini_client,review_agent,cost_table,prompt_registry}`.

## Tests
All tests mock both the scorer (`score`) and the agent (`run_review`) so they
don't hit the Gemini API.

- `test_run_eval_writes_report_file` — mock run_review returns 1 comment, mock
  score returns a CategoryResult, assert report JSON file exists at expected path
- `test_report_has_required_keys` — report JSON contains `timestamp`, `model`,
  `total_examples`, `total_cost_usd`, `by_category`, `overall`
- `test_skipped_examples_counted` — mock run_review raises ReviewError, assert
  `skipped_examples == 1` in report and no crash
- `test_cost_accumulator_sums_tokens` — call `complete()` twice with mocked
  inner client returning known token counts, assert `total_cost_usd` is correct

## Acceptance criteria
1. `python -m app.eval.runner --dataset eval_data/seed.jsonl --model gemini-2.0-flash --prompt-version 2`
   produces a valid JSON report in `eval_reports/`
2. Two consecutive runs produce two distinct report files (different timestamps)
3. Report JSON contains all keys in the shape above
4. Examples where the agent returns malformed output are counted in
   `skipped_examples` and do not crash the run
5. `pytest tests/test_eval_runner.py -v` → 4 tests pass
6. `pytest tests/ -v` → all 109 existing tests pass

## Note
`score()` raises `NotImplementedError` until Pratham implements it. The
acceptance criteria above are achievable only after Pratham fills in the body.
The tests mock `score()` so they pass regardless.
