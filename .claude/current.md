# current.md — Project State

**Reading order at session start:** 1) `CLAUDE.md`, 2) this file.
**When to update:** at the end of every feature, before merging the PR (see Update protocol below).

---

## Snapshot

Everything a fresh Claude Code session needs to know in 30 seconds.

- **Current phase:** Phase 7 — Observability (1/3)
- **Last merged:** Feature 22 — structured-logging
- **In progress:** —
- **Next up:** Feature 23 — llm-call-tracing
- **Total shipped:** 22 / 31

---

## Progress by phase

Keep the current phase expanded. Compress completed phases to a single line (`N/N ✓`).

### Phase 1 — Foundation (2/2 ✓)

### Phase 2 — GitHub Integration (4/4 ✓)

### Phase 3 — Async Processing (3/3 ✓)

### Phase 4 — Code Understanding (4/4 ✓)

### Phase 5 — Static Analysis (3/3 ✓)

### Phase 6 — LLM Review (5/5 ✓)

### Phase 7 — Observability (1/3)
- [x] 22 — structured-logging
- [ ] 23 — llm-call-tracing
- [ ] 24 — metrics-endpoint

### Phase 8 — Evaluation (0/3)
- [ ] 25 — eval-dataset-schema
- [ ] 26 — eval-runner
- [ ] 27 — eval-ci

### Phase 9 — Deployment (0/4)
- [ ] 28 — production-dockerfile
- [ ] 29 — github-actions-ci
- [ ] 30 — cloud-deploy
- [ ] 31 — github-app-prod

---

## Key decisions

Design choices made in shipped features that constrain future work. One line each, tagged with feature ref.

- [F17] LLM stack switched from Claude API to **Gemini API** (`google-genai==1.16.1`). `CLAUDE_API_KEY` renamed to `GEMINI_API_KEY` throughout. `google.genai.errors.ClientError`/`ServerError` are the SDK's own exception types — not `google.api_core.exceptions`.
- [F02] `pydantic-settings` is the sole config source; all modules must import `get_settings()` from `app.config` — no direct `os.environ` reads anywhere in app code.
- [F03] Signature verification always runs before JSON parsing — 401 must be returned before touching the payload.
- [F05] `GitHubAppAuth` takes a PEM string (not a file path) — caller reads the file. Pattern: `GitHubAppAuth(app_id=settings.GITHUB_APP_ID, private_key=Path(settings.GITHUB_PRIVATE_KEY_PATH).read_text())`.
- [F05] Token cache is in-memory per `GitHubAppAuth` instance; each worker process has its own cache. Cross-worker sharing deferred to Phase 3 (Celery/Redis).
- [F06] `fetch_pr_diff` takes `auth: GitHubAppAuth` as a keyword-only arg — caller owns the instance and its token cache. Never constructs its own `GitHubAppAuth` internally.
- [F08] `celery_app` created at module level with hardcoded default broker URL — do NOT call `get_settings()` at module level in `app/tasks/`. Call `configure_celery(redis_url)` instead; `app/main.py` does this in lifespan.
- [F09] Tests that trigger `review_pr.delay()` must patch `app.routes.webhooks.review_pr` (the whole task) to avoid Redis connection attempts. Tests that exercise the task itself use `task_always_eager = True` + mock `_get_auth` and `fetch_pr_diff`.

---

## Public interfaces

Function signatures, endpoints, schemas, and file locations that future features will import or depend on. Copy the signature exactly — this is the contract.

Format:
```
[F<NN>] <module.path>.<name>(<sig>) -> <return>
[F<NN>] <METHOD> <endpoint> -> <response shape>
[F<NN>] <file path> — <what lives here>
```

- [F01] `GET /health -> {"status": "ok"}` (200)
- [F02] `app.config.get_settings() -> Settings` — call this; never read env vars directly
- [F02] `app.config.Settings` — fields: `GITHUB_APP_ID`, `GITHUB_WEBHOOK_SECRET`, `GITHUB_PRIVATE_KEY_PATH`, `GEMINI_API_KEY` (all `str`, required); `REDIS_URL` (`str`, default `"redis://localhost:6379/0"`)
- [F02] `tests/conftest.py` — autouse fixture sets dummy env vars + clears `lru_cache` after each test; all future test files inherit this automatically
- [F03] `POST /webhooks/github` → 200 (handled PR event), 204 (ignored event), 401 (bad/missing signature)
- [F03] `app.routes.webhooks._verify_signature(secret, body, header) -> bool` — private; do not call from outside this module
- [F05] `app.github.auth.GitHubAppAuth(app_id: str, private_key: str) -> None` — constructor; raises `ValueError` on bad PEM
- [F05] `app.github.auth.GitHubAppAuth.get_installation_token(installation_id: int) -> str` — returns cached or fresh installation access token; raises `httpx.HTTPStatusError` on GitHub API failure
- [F06] `app.github.diff.fetch_pr_diff(repo: str, pr_number: int, installation_id: int, *, auth: GitHubAppAuth) -> str` — returns raw unified diff text
- [F06] `app.github.exceptions.GitHubAPIError` — base; `PRNotFoundError` (404), `PRAccessDeniedError` (403), `GitHubServerError` (5xx)
- [F08] `app.tasks.celery_app` — the Celery instance; import this to register new tasks
- [F08] `app.tasks.configure_celery(redis_url: str) -> None` — call once at startup; already wired in `app/main.py` lifespan
- [F08] `app.tasks.ping.ping` — registered as `"tasks.ping"`; use as template for new tasks
- [F09] `app.tasks.review.review_pr(repo: str, pr_number: int, installation_id: int) -> None` — registered as `"tasks.review_pr"`; enqueue via `.delay()`
- [F09] `app.tasks.review._get_auth() -> GitHubAppAuth` — lazy singleton; resolves `[F05+F06→F09]` tech debt
- [F10] `app.parser.python.parse_python(source: str) -> list[Symbol]` — returns symbols in source order; module-level `_PARSER` is safe to import at any time
- [F10] `app.parser.python.Symbol` — `dataclass(frozen=True)`: `name: str`, `kind: str` (`"function"|"class"`), `start_line: int`, `end_line: int` (both 1-indexed; decorated defs use decorator's line as `start_line`)
- [F11] `app.parser.diff.parse_diff(raw: str) -> list[FileDiff]` — splits on `diff --git`, skips binary/rename sections, returns one `FileDiff` per parseable file
- [F11] `app.parser.diff.FileDiff` — `dataclass`: `path: str`, `hunks: list[Hunk]`
- [F11] `app.parser.diff.Hunk` — `dataclass`: `old_range: Range`, `new_range: Range`, `lines: list[str]` (each line keeps its leading `+`/`-`/` ` prefix)
- [F11] `app.parser.diff.Range` — `dataclass`: `start: int`, `count: int` (1-indexed; new files use `Range(0, 0)` for old_range)
- [F12] `app.parser.hunk.symbols_touched(hunk: Hunk, symbols: list[Symbol]) -> list[Symbol]` — returns symbols whose line range overlaps the hunk's new_range; returns `[]` for pure-deletion hunks (count == 0)
- [F13] `app.github.context.ContextExpander(auth: GitHubAppAuth)` — owns per-instance `(sha, path)` cache; create one per review run
- [F13] `ContextExpander.expand_context(repo, sha, path, symbol, installation_id, *, padding=10) -> str` — fetches file via GitHub Contents API (raw), slices symbol ± padding lines; raises `FileNotFoundAtSHA` on 404
- [F13] `app.github.exceptions.FileNotFoundAtSHA(GitHubAPIError)` — raised when file path not found at given SHA
- [F14] `app.analysis.finding.Finding` — `dataclass(frozen=True)`: `path: str`, `line: int`, `col: int`, `rule: str`, `message: str` — shared schema for F15 + F16
- [F14] `app.analysis.finding.RuffError` — raised when ruff exits with code ≥ 2 or cannot be found
- [F14] `app.analysis.ruff_runner.run_ruff(files: dict[str, str]) -> list[Finding]` — writes sources to temp dir, invokes ruff CLI, maps findings back to original path keys
- [F15] `app.analysis.mypy_runner.run_mypy(files: dict[str, str]) -> list[Finding]` — same pattern as run_ruff; parses NDJSON output; drops `severity="note"` lines; uses `--ignore-missing-imports`
- [F15] `Finding.severity: str = "error"` — added in F15; ruff findings hardcode `"error"`, mypy findings use the value from mypy's JSON output
- [F15] `app.analysis.finding.MypyError` — raised when mypy exits with code ≥ 2
- [F16] `app.analysis.aggregator.aggregate(findings: list[Finding], diff: list[FileDiff]) -> list[Finding]` — keeps only findings whose `(path, line)` lands on a `+` line in the diff
- [F16] `app.analysis.aggregator._added_lines(diff) -> dict[str, set[int]]` — builds `{path: {new-file line numbers of + lines}}`; `-` lines don't advance the counter
- [F17] `app.llm.GeminiClient` — wraps `google-genai` SDK; create one instance per review run
- [F17] `app.llm.GeminiClient.complete(messages, *, model, max_tokens, system=None) -> GeminiResponse` — retries 3× on rate-limit/server errors; raises `LLMRateLimitError`, `LLMServerError`, or `LLMClientError`
- [F17] `app.llm.GeminiResponse` — `dataclass(frozen=True)`: `content: str`, `input_tokens: int`, `output_tokens: int`
- [F17] `app.llm.exceptions` — `LLMError` (base), `LLMRateLimitError`, `LLMServerError`, `LLMClientError`
- [F18] `app.llm.PromptRegistry(root=_PROMPTS_ROOT)` — `get(name: str, version: int) -> str`; raises `PromptNotFoundError` on missing file
- [F18] `prompts/review/v1.md` — seed prompt with `{diff}`, `{context}`, `{findings}` slots; F19 may refine
- [F18] `app.llm.PromptNotFoundError(LLMError)` — raised when prompt file does not exist
- [F19] `app.llm.Comment` — Pydantic model: `path: str`, `line: int`, `body: str`, `severity: Literal["error","warning","suggestion"]`
- [F19] `app.llm.run_review(diff, context, findings, *, client, registry, model, prompt_version=1) -> list[Comment]` — calls Gemini, parses JSON, validates; raises `ReviewError` on bad output
- [F19] `app.llm.ReviewError(LLMError)` — raised on non-JSON or schema-invalid model response
- [F20] `app.github.poster.post_review(repo, pr_number, installation_id, comments, *, auth) -> None` — single POST to GitHub Create Review API; no-op if comments empty; severity prepended to body as `[error]`/`[warning]`/`[suggestion]`
- [F21] `app.llm.load_style_guide(path=_DEFAULT_PATH) -> str` — reads `style_guide.yaml`, returns bullet list of rules for `{style_guide}` slot; raises `StyleGuideError` on any failure
- [F21] `style_guide.yaml` — project-root YAML with `rules` list; edit to change prompt style rules without touching Python
- [F21] `prompts/review/v2.md` — full prompt with `{style_guide}`, `{diff}`, `{context}`, `{findings}` slots
- [F22] All modules use `structlog.get_logger()` — no stdlib `logging.getLogger` in app code
- [F22] `app.middleware.correlation.CorrelationMiddleware` — binds `request_id` UUID per request via `structlog.contextvars`; stashes on `request.state.request_id` for task propagation
- [F22] `review_pr` task accepts `correlation_id: str | None` kwarg and binds it to structlog context at task start

---

## Tech debt

Things left half-done, brittle, or worked around. Link to the future feature that will fix it when possible.

- _(none)_

---

## Update protocol

When a feature merges to `main`, before closing the session:

1. **Snapshot:** move the feature from `In progress` to `Last merged`; increment `Total shipped`; set `Next up` to the following roadmap item.
2. **Progress by phase:** tick the feature's checkbox. Update the phase's `X/N` count. If the phase is now complete, collapse it to a single `N/N ✓` line.
3. **Key decisions:** if a decision was made during this feature that affects future work (library choice, schema, auth approach, tradeoff taken), add a line tagged `[F<NN>]`.
4. **Public interfaces:** if the feature introduced something future features will call/import/hit, add the exact signature or endpoint shape. This is the most important section — future Claude Code sessions read it to avoid re-deriving contracts.
5. **Tech debt:** if anything was skipped, mocked, hardcoded, or left brittle, log it with a pointer to the feature that should fix it.
6. **Also update `CLAUDE.md` §11** — flip the feature's status marker there too (`[ ]` → `[x]`).
7. **Also append to `LEARNINGS.md`** — at least one surprise + one decision from this feature.
8. Keep this file under ~200 lines. If it grows past that, condense older Key decisions and Tech debt entries.

---

## Session kickoff (what Claude Code should do)

At the start of every session, before touching anything:

1. Read `CLAUDE.md` in full.
2. Read this file in full.
3. Confirm with Pratham: "Working on Feature `<NN>: <name>` — is that correct?"
4. Proceed to §4 step 5 of `CLAUDE.md` (generate the spec).
