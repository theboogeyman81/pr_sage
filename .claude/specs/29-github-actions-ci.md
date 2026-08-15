# Feature 29: github-actions-ci

## Goal
A CI workflow that runs tests, linters, and type checks on every push and PR, and verifies the production Docker image builds cleanly.

## In scope
- `.github/workflows/ci.yml` — new workflow with three jobs: `test`, `lint`, `typecheck`, `docker-build`
- `[tool.mypy]` config added to `pyproject.toml` (needed for a reproducible mypy invocation in CI)
- Triggers on every `push` and every `pull_request` targeting `main`
- Python 3.11 only (no matrix)
- Redis service container available to the `test` job (for future integration tests; current tests mock it)
- `docker-build` job runs `docker build` to validate the Dockerfile from Feature 28

## Out of scope
- Deploying the image (Feature 30)
- Publishing the image to a registry
- Branch protection rule configuration (done in GitHub UI, not code)
- Eval in this workflow — `eval.yml` (Feature 27) already runs eval on PRs that touch `prompts/`, `app/llm/`, or `eval_data/`; duplicating it here would double Gemini API costs for no gain

## File structure
```
.github/
    workflows/
        ci.yml              ← new
pyproject.toml              ← modified ([tool.mypy] section added)
```

## Contracts

### Workflow triggers
```yaml
on:
  push:
    branches: ["**"]
  pull_request:
    branches: [main]
```

### Jobs

#### `test`
- `runs-on: ubuntu-latest`
- Redis service: `redis:7-alpine`, port 6379, healthcheck `redis-cli ping`
- Steps: checkout → setup-python 3.11 → `pip install -e ".[dev]"` → `pytest`
- Env vars needed (satisfy `Settings` validation — monkeypatch handles it per-test but module-level imports may instantiate Settings early):
  ```yaml
  env:
    GITHUB_APP_ID: ci-placeholder
    GITHUB_WEBHOOK_SECRET: ci-placeholder
    GITHUB_PRIVATE_KEY: ci-placeholder
    GEMINI_API_KEY: ci-placeholder
    REDIS_URL: redis://localhost:6379/0
  ```

#### `lint`
- `runs-on: ubuntu-latest`
- Steps: checkout → setup-python 3.11 → `pip install ruff==0.16.1` → `ruff check app/`
- No app env vars needed

#### `typecheck`
- `runs-on: ubuntu-latest`
- Steps: checkout → setup-python 3.11 → `pip install -e .` → `mypy app/`
- No app env vars needed

#### `docker-build`
- `runs-on: ubuntu-latest`
- Steps: checkout → `docker build -t pr-sage .`
- No env vars needed (build-time only, no runtime secrets)

### `[tool.mypy]` config (pyproject.toml)
```toml
[tool.mypy]
python_version = "3.11"
ignore_missing_imports = true
```
`ignore_missing_imports = true` is required because several deps (tree-sitter-python, google-genai, structlog, celery) lack complete type stubs.

## Dependencies
No new Python packages. GitHub Actions runners include Docker.

## Tests
No new tests for this feature — the workflow itself is the deliverable.

## Acceptance criteria
1. Opening a PR to `main` on this repo triggers the `ci` workflow in GitHub Actions
2. All four jobs (`test`, `lint`, `typecheck`, `docker-build`) pass on the current codebase
3. Introducing a deliberate ruff violation causes the `lint` job to fail
4. Introducing a failing test causes the `test` job to fail
5. `docker-build` job completes without error (validates Feature 28's Dockerfile)
