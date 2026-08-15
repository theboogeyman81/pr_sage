# Feature 27: Eval CI

## Goal
Run the eval-runner automatically on PRs that touch prompts or agent code,
failing the build if overall precision drops below a configurable threshold.

## In scope
- `.github/workflows/eval.yml` — GitHub Actions workflow
- Add `--fail-below FLOAT` argument to `app/eval/runner.py` `_main()`:
  after writing the report, read `overall.precision` from it; exit 1 if below
  the threshold (default 0.0 so existing CLI usage is unchanged)
- Test for the new CLI argument in `tests/test_eval_runner.py`

## Out of scope
- Performance benchmarking
- Caching Gemini API responses between CI runs
- Matrix builds or multiple Python versions (one version only: 3.11)
- Uploading the report file as a CI artifact (nice-to-have for later)

## File structure
```
.github/
    workflows/
        eval.yml           ← new
app/eval/
    runner.py              ← modified (_main adds --fail-below)
tests/
    test_eval_runner.py    ← modified (1 new test)
```

## Contracts

### `--fail-below` CLI argument
Added to `_main()` in `app/eval/runner.py`:
```
python -m app.eval.runner \
    --dataset eval_data/seed.jsonl \
    --model gemini-2.0-flash \
    --prompt-version 2 \
    --output-dir eval_reports/ \
    --fail-below 0.5
```
- Reads overall precision from the written JSON report
- If `overall["precision"] < fail_below`: prints a message to stderr, exits 1
- If `fail_below` omitted or 0.0: no threshold check (backward-compatible)

### `.github/workflows/eval.yml`

Triggers on `push` and `pull_request` for paths:
```yaml
paths:
  - 'prompts/**'
  - 'app/llm/**'
  - 'eval_data/**'
```

Steps:
1. `actions/checkout@v4`
2. `actions/setup-python@v5` with `python-version: '3.11'`
3. `pip install -e .`
4. Run eval + threshold check in one step:
   ```bash
   python -m app.eval.runner \
     --dataset eval_data/seed.jsonl \
     --model gemini-2.0-flash \
     --prompt-version 2 \
     --output-dir eval_reports/ \
     --fail-below 0.5
   ```
5. Print report to stdout for visibility:
   ```bash
   cat eval_reports/*.json
   ```

Secrets/env vars in the workflow:
```yaml
env:
  GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
  GITHUB_APP_ID: "ci-placeholder"
  GITHUB_WEBHOOK_SECRET: "ci-placeholder"
  GITHUB_PRIVATE_KEY_PATH: "/dev/null"
  # REDIS_URL has a default — no need to set
```
(`GITHUB_APP_ID`, `GITHUB_WEBHOOK_SECRET`, `GITHUB_PRIVATE_KEY_PATH` are
required by `Settings` but unused during eval. Dummy values prevent boot failure.)

## Dependencies
No new packages. GitHub Actions uses `ubuntu-latest`.

## Tests
One new test added to `tests/test_eval_runner.py`:

- `test_fail_below_exits_nonzero_when_precision_low`: use
  `subprocess.run(["python", "-m", "app.eval.runner", "--dataset", ...,
  "--fail-below", "0.99", ...])` with mocked eval data that produces
  precision=0.0 (all skipped), assert `returncode != 0`

  **Alternative** (simpler, no subprocess): extract the threshold check into a
  helper `_check_threshold(report: dict, fail_below: float) -> bool` and test
  that directly — no need for subprocess.

  Use the helper approach: add `_check_threshold` as a module-level function,
  test it with a report dict.

## Acceptance criteria
1. Opening a PR that changes any file under `prompts/` or `app/llm/` triggers
   the `eval` workflow in GitHub Actions
2. The workflow passes when overall precision ≥ 0.5
3. The workflow exits with non-zero status when overall precision < `--fail-below`
4. `GEMINI_API_KEY` is the only real secret required; GitHub auth fields use
   placeholder values
5. New test passes: `pytest tests/test_eval_runner.py -v` → all 5 tests green
6. Full suite: `pytest tests/ -v` → all 122 existing tests pass
