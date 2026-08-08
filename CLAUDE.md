# CLAUDE.md — LLM-Powered Code Review Bot

This file is the operating manual for building this project with Claude Code.
Read it in full at the start of every session.

---

## 1. Project

A GitHub PR review bot: listens for PR events, fetches the diff, understands
the code, runs static analysis, asks an LLM to review, and posts comments back
to the PR. Production-grade, deployed, actually usable.

Owner: Pratham. Time budget: ~15 hrs/week.

---

## 2. Stack (defaults — soft-locked)

Use these unless you have a strong technical reason not to. If you want to
deviate, stop and propose the alternative with a one-paragraph justification
before writing code.

- **Language:** Python 3.11+
- **Web:** FastAPI + Uvicorn
- **Async jobs:** Celery + Redis
- **GitHub auth:** GitHub App (JWT → installation token), **not** PATs
- **LLM:** Gemini API (Google). Ollama as a fallback only if cost blocks progress
- **Code parsing:** tree-sitter
- **Static analysis:** ruff (lint), mypy (types)
- **Container:** Docker + docker-compose for dev
- **Deploy target:** Fly.io or Railway (free tier)
- **Reviewed languages (bot's target):** **Python only** for v1

Pin every dependency. No unpinned versions in `pyproject.toml`.

---

## 3. Roles (do not blur these)

### Pratham (human)
- Reviews every spec, plan, and diff before accepting
- Writes tricky logic himself: the agent loop, prompt design, eval logic
- Maintains `LEARNINGS.md` (surprises, bugs, decisions)
- Makes design tradeoffs when Claude Code surfaces them

### Claude Code (this tool)
- Generates spec docs from the roadmap entry in this file
- Generates plan docs from spec docs
- Implements plans (boilerplate, infra, wiring)
- Explains concepts when asked, one at a time
- Never implements beyond the current feature's spec

### Chat (claude.ai) — use sparingly
- Only when Claude Code is stuck or Pratham wants a concept deep-dive
- Not for spec/plan/code writing (that's Claude Code's job)

---

## 4. Per-feature workflow

Every feature follows these 16 steps. One feature = one session = one branch = one PR.

1. Start a fresh Claude Code session
2. Rename the session to the feature name (e.g. `webhook-receiver`)
3. `git pull origin main`
4. `git checkout -b feature/<slug>`
5. Ask Claude Code to generate the spec (see §5). Claude Code saves it to `.claude/specs/<NN>-<slug>.md`
6. Pratham reviews the spec. Requests changes if needed. **Do not skip.**
7. Once approved, Claude Code enters plan mode, reads the spec + existing code, produces the plan, saves to `.claude/plans/<NN>-<slug>.md`
8. Pratham reviews the plan. Approves or iterates.
9. Claude Code implements. Show diffs file-by-file for review.
10. Pratham validates against the spec's acceptance criteria manually
11. Iterate if any criterion fails
12. `git add . && git commit -m "<slug>: <short summary>"`
13. `git push origin feature/<slug>`
14. Open PR, self-review, merge
15. `git checkout main && git pull`
16. `git branch -D feature/<slug>`

Then update `LEARNINGS.md` with at least one entry before starting the next feature.

---

## 5. Spec document format

Claude Code generates specs using this exact structure. Save to
`.claude/specs/<NN>-<slug>.md`.

```markdown
# Feature <NN>: <Name>

## Goal
<one sentence>

## In scope
- <bullet>
- <bullet>

## Out of scope
- <what this feature deliberately does NOT do>
- <what belongs to a future feature>

## File structure
<tree of new/modified files>

## Contracts
<endpoint shapes, function signatures, data schemas — anything with a defined interface>

## Dependencies
- <package>==<pinned version>

## Tests
- <test name>: <what it asserts>

## Acceptance criteria
1. <observable behavior 1>
2. <observable behavior 2>
...
```

After saving, Claude Code must list any ambiguities it noticed in the roadmap
entry that Pratham should resolve before plan mode.

---

## 6. Plan document format

Save to `.claude/plans/<NN>-<slug>.md`.

```markdown
# Plan: Feature <NN> — <Name>

## Files to create
- <path>: <purpose>

## Files to modify
- <path>: <what changes and why>

## Implementation order
1. <step> — <why first>
2. <step>

## Open questions
- <anything the spec left ambiguous>
```

Plan mode = no code written yet. Just the plan file + a summary in chat.

---

## 7. Diff review checklist

Before accepting any Claude Code diff, Pratham checks:

- [ ] File tree matches the plan. No surprise files.
- [ ] Nothing outside the current feature's scope was touched
- [ ] Dependencies are pinned to exact versions
- [ ] No stubs or imports referencing future features
- [ ] Tests actually assert behavior, not just "no exception"
- [ ] Secrets read from env, never hardcoded
- [ ] Error paths handled (network, timeouts, bad input) where the spec calls for it
- [ ] Log statements don't leak secrets or full request bodies
- [ ] No `TODO` / `FIXME` left without a linked issue

---

## 8. Guardrails (Claude Code must obey)

**Never:**
- Implement more than what the current feature's spec covers
- Skip writing tests to "save time"
- Use `==` for HMAC or token comparisons — always `hmac.compare_digest`
- Leave dependency versions unpinned
- Commit `.env` files or private keys
- Log webhook payloads, PR diffs, or LLM prompts/completions at INFO level (DEBUG only, and even then redacted)
- Reference future features in code (no `# TODO: wire this to celery later`)
- Silently change stack choices from §2 — propose first

**Always:**
- Read `CLAUDE.md` at session start
- Read the previous feature's spec + code before generating a new spec
- Ask Pratham before editing files outside the current feature's scope
- Show diffs file-by-file, not all at once
- Push back if Pratham asks for something that violates these guardrails

---

## 9. Session kickoff prompt

At the start of every new Claude Code session, Pratham pastes:

> Read `CLAUDE.md`. I'm starting **Feature <NN>: <name>** (see §11 roadmap).
> Follow the per-feature workflow from §4. Begin at step 5: generate the spec
> per §5, save it to `.claude/specs/<NN>-<slug>.md`, then stop and show it to
> me for review. Do not enter plan mode until I approve.

---

## 10. When to come back to chat (claude.ai)

Only for:
- A concept Pratham wants explained in depth (tree-sitter internals, HMAC theory, Celery's task routing model, etc.)
- Claude Code is stuck in a loop
- A design decision that affects multiple future phases
- Reviewing an eval methodology or prompt strategy

Not for: generating specs, generating plans, writing code, reviewing diffs.
Claude Code handles all of that.

---

## 11. Roadmap

Phases must be completed in order. Features within a phase mostly in order,
but Claude Code may propose reordering with justification.

Feature status legend: `[ ]` not started · `[~]` in progress · `[x]` merged

---

### Phase 1 — Foundation

Get a boot-able FastAPI app with tests, logging, and config plumbing.

#### `[x]` Feature 01 — project-scaffold
- **Goal:** Runnable FastAPI app with `/health`, tests green, project layout ready for growth.
- **In scope:** `app/` package, `pyproject.toml` with pinned deps, `/health` endpoint returning `{"status":"ok"}`, stdlib logging configured once, one pytest for `/health`, `.gitignore`, `.env.example`, `README.md`.
- **Out of scope:** webhooks, GitHub, Celery, Docker.
- **Accept:** `uvicorn app.main:app` boots · `curl /health` returns `{"status":"ok"}` 200 · `pytest` passes · logs appear on stdout.

#### `[x]` Feature 02 — config-management
- **Goal:** Centralized, validated config from env vars.
- **In scope:** `pydantic-settings` based `Settings` class, loaded once, fails fast on missing required vars. Placeholders for `GITHUB_APP_ID`, `GITHUB_WEBHOOK_SECRET`, `GITHUB_PRIVATE_KEY_PATH`, `CLAUDE_API_KEY`, `REDIS_URL`. Tests for required/optional handling.
- **Out of scope:** actually using any of these values yet.
- **Accept:** app fails to boot with a clear error if a required var is missing · tests cover required/optional/default behavior.

---

### Phase 2 — GitHub Integration

Receive webhook events, authenticate as a GitHub App, fetch PR diffs.

#### `[x]` Feature 03 — webhook-receiver
- **Goal:** `POST /webhooks/github` accepts PR events with HMAC-SHA256 verified signatures.
- **In scope:** endpoint reads raw body once, verifies `X-Hub-Signature-256` using `hmac.compare_digest`, filters to `pull_request` events with action in `{opened, synchronize, reopened}`, returns 200 fast (<1s), 401 on bad signature, 204 on ignored event. Tests: valid sig, forged sig, ignored event.
- **Out of scope:** any actual work on the PR — just log delivery ID + repo + PR#.
- **Accept:** all 3 tests pass · endpoint returns in <100ms locally.

#### `[x]` Feature 04 — dev-tunnel-docs
- **Goal:** Document the dev tunnel setup so PRs on real repos hit the local server.
- **In scope:** README section covering `smee.io` (or `cloudflared`) — install, start command, forwarding to `localhost:8000/webhooks/github`. GitHub App creation checklist (permissions, events, webhook secret).
- **Out of scope:** code.
- **Accept:** following the README from a clean laptop, Pratham can open a PR on a test repo and see the delivery hit the local server.

#### `[x]` Feature 05 — github-app-auth
- **Goal:** Given `GITHUB_APP_ID`, private key, and an installation ID, produce an installation access token.
- **In scope:** `GitHubAppAuth` class with `get_installation_token(installation_id)`. JWT signed with RS256, cached until expiry (10 min JWT, 1 hour token). Tests with a fake private key.
- **Out of scope:** using the token yet.
- **Accept:** returns valid-shaped token · caches (second call within TTL doesn't hit GitHub) · tests pass.

#### `[x]` Feature 06 — pr-diff-fetch
- **Goal:** Given a webhook event, fetch the PR's unified diff via GitHub API.
- **In scope:** `fetch_pr_diff(repo, pr_number, installation_id)` returns the raw diff text. Uses installation token from Feature 05. Handles 404/403/5xx with typed exceptions. Tests with mocked HTTP.
- **Out of scope:** parsing the diff.
- **Accept:** returns a diff on a real test PR · typed exceptions on failure paths · tests pass.

---

### Phase 3 — Async Processing

Move heavy work off the webhook path.

#### `[x]` Feature 07 — docker-compose-dev
- **Goal:** `docker-compose up` brings up Redis for local dev.
- **In scope:** `docker-compose.yml` with Redis 7 service, volume, healthcheck. README updated.
- **Out of scope:** app in Docker (later, prod).
- **Accept:** `docker-compose up -d` · `redis-cli ping` returns PONG.

#### `[x]` Feature 08 — celery-scaffold
- **Goal:** Celery app with a dummy task; worker starts and consumes.
- **In scope:** `app/tasks/` package, Celery config reading `REDIS_URL` from settings, one `ping()` task that logs and returns "pong". Test that submits and awaits.
- **Out of scope:** wiring to webhook.
- **Accept:** `celery -A app.tasks worker` starts · `ping.delay()` executes · test passes.

#### `[x]` Feature 09 — webhook-enqueue
- **Goal:** Webhook enqueues a task; task fetches the PR diff.
- **In scope:** new task `review_pr(repo, pr_number, installation_id)` that calls Feature 06's fetcher and logs a summary (files changed, +/- lines). Webhook enqueues this task instead of just logging. Integration test: forged webhook → task queued → task ran (in-memory eager mode for tests).
- **Out of scope:** actually reviewing anything.
- **Accept:** real PR event → task runs on worker → logs show diff summary.

---

### Phase 4 — Code Understanding

Understand code structure, not just text.

#### `[x]` Feature 10 — tree-sitter-python
- **Goal:** Parse Python source into an AST and enumerate top-level defs.
- **In scope:** `parse_python(source: str) -> list[Symbol]` returning function/class names + line ranges. Uses `tree-sitter-python`. Tests over a small fixture file.
- **Out of scope:** cross-file resolution.
- **Accept:** correctly identifies functions, methods, classes with accurate line ranges.

#### `[x]` Feature 11 — diff-parser
- **Goal:** Parse a unified diff into structured hunks per file.
- **In scope:** `parse_diff(raw: str) -> list[FileDiff]` with `FileDiff(path, hunks: list[Hunk(old_range, new_range, lines)])`. Tests over a small fixture diff.
- **Out of scope:** binary diffs, renames-with-content (skip cleanly).
- **Accept:** correct file/hunk/line ranges on fixtures · skips unsupported cases without crashing.

#### `[ ]` Feature 12 — hunk-to-symbol
- **Goal:** Given a hunk and the file's parsed symbols, identify which symbols the hunk touches.
- **In scope:** `symbols_touched(hunk, symbols) -> list[Symbol]`. Handles hunks that cross symbol boundaries.
- **Out of scope:** call-graph analysis.
- **Accept:** unit tests over 5+ hunk placements (inside, crossing, at boundary, outside all symbols, inside nested class).

#### `[ ]` Feature 13 — context-expansion
- **Goal:** For each touched symbol, fetch the whole symbol body from the head SHA + N surrounding lines.
- **In scope:** `expand_context(repo, sha, path, symbol, padding=10)` fetches file via GitHub API and slices. Cache per (sha, path) to avoid refetching.
- **Out of scope:** cross-file context (imports, callers).
- **Accept:** returns full symbol source · cache hit on second call for same file.

---

### Phase 5 — Static Analysis

#### `[ ]` Feature 14 — ruff-runner
- **Goal:** Run ruff on changed files, capture structured findings.
- **In scope:** `run_ruff(files: dict[path, source]) -> list[Finding]` using ruff's JSON output. Uses a temp dir. Tests with fixture files that trip a known rule.
- **Out of scope:** configurable rule set (Phase 6).
- **Accept:** returns findings with rule code, message, line, col.

#### `[ ]` Feature 15 — mypy-runner
- **Goal:** Same, for mypy.
- **In scope:** `run_mypy(files) -> list[Finding]`. Handle missing type stubs gracefully.
- **Out of scope:** whole-repo type checking.
- **Accept:** returns findings with severity, line, message · doesn't crash on files with missing imports.

#### `[ ]` Feature 16 — analysis-aggregator
- **Goal:** Merge ruff + mypy findings, filter to lines actually changed in the diff.
- **In scope:** `aggregate(findings, diff) -> list[Finding]` keeping only findings on `+` lines.
- **Out of scope:** dedup across tools.
- **Accept:** noise from unchanged lines filtered out · tests confirm.

---

### Phase 6 — LLM Review

#### `[x]` Feature 17 — gemini-api-client
- **Goal:** Robust wrapper around the Gemini API.
- **In scope:** `GeminiClient.complete(messages, ...) -> GeminiResponse` with exponential-backoff retry on 429/5xx, typed errors (`LLMRateLimitError`, `LLMServerError`, `LLMClientError`), response wrapper exposing tokens.
- **Out of scope:** streaming, multimodal inputs.
- **Accept:** 8 unit tests with mocked SDK cover success, retry, permanent-fail paths.

#### `[x]` Feature 18 — prompt-registry
- **Goal:** Prompts live as versioned files, loaded by name+version.
- **In scope:** `prompts/<name>/v<N>.md` layout. `PromptRegistry.get(name, version) -> str`. Version must be explicit at call sites — no "latest" default.
- **Out of scope:** templating language (use Python `.format` for now).
- **Accept:** load succeeds on valid name/version, raises on missing.

#### `[x]` Feature 19 — review-agent-v1
- **Goal:** Given diff, expanded context, and static findings, produce a structured review.
- **In scope:** Pratham writes the agent loop. It calls Feature 17 with a prompt from Feature 18, gets back JSON with `list[Comment(path, line, body, severity)]`. Validated with Pydantic.
- **Out of scope:** multi-turn agent, tool use.
- **Accept:** on a fixture diff, produces valid-shape output · fails cleanly on malformed model output.

#### `[x]` Feature 20 — github-comment-poster
- **Goal:** Post the agent's comments back to the PR as a review.
- **In scope:** `post_review(repo, pr_number, installation_id, comments)` using GitHub's Create Review API. One review with N comments, not N individual comments.
- **Out of scope:** updating an existing review on `synchronize`.
- **Accept:** posts a review visible on the PR with all comments attached to correct file+line.

#### `[ ]` Feature 21 — style-guide-config
- **Goal:** A YAML file defines review rules; contents get injected into the prompt.
- **In scope:** `style_guide.yaml` schema, loader, injection into the review prompt (new prompt version). Example rules.
- **Out of scope:** per-repo overrides.
- **Accept:** changing the YAML changes the prompt content · tests over parse errors.

---

### Phase 7 — Observability

#### `[ ]` Feature 22 — structured-logging
- **Goal:** Replace stdlib logging with structlog; every log line has correlation IDs.
- **In scope:** structlog config, request ID middleware, task ID propagation into Celery.
- **Out of scope:** log shipping (later, deploy).
- **Accept:** every log line for a single PR shares one correlation ID across API + worker.

#### `[ ]` Feature 23 — llm-call-tracing
- **Goal:** Every Claude API call logs prompt-hash, tokens in/out, cost estimate, duration, correlation ID.
- **In scope:** wrapper around Feature 17 that emits one structured log per call. Cost table for the model used.
- **Out of scope:** persistent trace DB.
- **Accept:** trace log line per call · totals aggregatable via `jq`.

#### `[ ]` Feature 24 — metrics-endpoint
- **Goal:** `/metrics` endpoint in Prometheus format.
- **In scope:** `prometheus-client`, counters (reviews_total, llm_calls_total, errors_total), histograms (review_duration_seconds, tokens_per_review).
- **Out of scope:** Grafana dashboards.
- **Accept:** `curl /metrics` returns valid Prometheus format · counters increment on real events.

---

### Phase 8 — Evaluation

#### `[ ]` Feature 25 — eval-dataset-schema
- **Goal:** Define the format for labeled review examples.
- **In scope:** JSONL schema: `{diff, context, expected_findings: list[{path, line_range, category}], notes}`. Loader + validator. Seed dataset with 5–10 examples Pratham labels by hand.
- **Out of scope:** eval scoring (next feature).
- **Accept:** loader validates schema · at least 5 real examples committed.

#### `[ ]` Feature 26 — eval-runner
- **Goal:** Run the review agent against the dataset and score it.
- **In scope:** Pratham writes the scoring logic (precision/recall on finding location + category matches). Report table by category. Costs total.
- **Out of scope:** LLM-judge scoring.
- **Accept:** produces a report file per run · Pratham can compare two runs.

#### `[ ]` Feature 27 — eval-ci
- **Goal:** Eval runs in CI on changes to prompts/ or agent code.
- **In scope:** GitHub Actions job, uses a cheap model or subset dataset for speed. Fails CI if precision drops below a threshold.
- **Out of scope:** perf benchmarking.
- **Accept:** CI runs on PRs · threshold-drop causes CI to fail.

---

### Phase 9 — Deployment

#### `[ ]` Feature 28 — production-dockerfile
- **Goal:** Multi-stage Dockerfile for app + worker (same image, different CMD).
- **In scope:** builder stage compiles wheels, runtime stage is slim + non-root. Healthcheck. `.dockerignore`.
- **Out of scope:** image publishing.
- **Accept:** image builds · runs both `uvicorn` and `celery worker` from same image.

#### `[ ]` Feature 29 — github-actions-ci
- **Goal:** CI runs tests + linters + type checks + a subset eval on every PR.
- **In scope:** `.github/workflows/ci.yml`, Python matrix (just 3.11), Redis service for integration tests.
- **Out of scope:** deploy.
- **Accept:** PR to the bot's own repo triggers CI · failing tests block merge.

#### `[ ]` Feature 30 — cloud-deploy
- **Goal:** Deploy to Fly.io (or Railway), get a public URL.
- **In scope:** `fly.toml` (or Railway config), secrets set, app + worker + Redis deployed, health check green.
- **Out of scope:** high availability.
- **Accept:** public URL responds to `/health` · worker logs visible.

#### `[ ]` Feature 31 — github-app-prod
- **Goal:** Point the real GitHub App at the deployed URL and prove end-to-end.
- **In scope:** update GitHub App webhook URL, install on a real test repo, open a real PR, verify review comment appears.
- **Out of scope:** onboarding others.
- **Accept:** a PR on a real repo gets a review comment from the bot within 60s.

---

## 12. Notes

- After each feature merges, update the status marker in §11 (`[ ]` → `[x]`).
- Add one entry per feature to `LEARNINGS.md`. Minimum: one surprise + one decision.
- If a feature turns out to be too big, split it and update §11 before starting.
- If the roadmap becomes wrong (learned something that invalidates a later feature), update it. This file is not immutable.
