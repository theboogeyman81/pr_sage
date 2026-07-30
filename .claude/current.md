# current.md — Project State

**Reading order at session start:** 1) `CLAUDE.md`, 2) this file.
**When to update:** at the end of every feature, before merging the PR (see Update protocol below).

---

## Snapshot

Everything a fresh Claude Code session needs to know in 30 seconds.

- **Current phase:** Phase 1 — Foundation
- **Last merged:** Feature 01 — project-scaffold
- **In progress:** Feature 02 — config-management
- **Next up:** Feature 03 — webhook-receiver
- **Total shipped:** 1 / 31

---

## Progress by phase

Keep the current phase expanded. Compress completed phases to a single line (`N/N ✓`).

### Phase 1 — Foundation (1/2)
- [x] 01 — project-scaffold
- [ ] 02 — config-management

### Phase 2 — GitHub Integration (0/4)
- [ ] 03 — webhook-receiver
- [ ] 04 — dev-tunnel-docs
- [ ] 05 — github-app-auth
- [ ] 06 — pr-diff-fetch

### Phase 3 — Async Processing (0/3)
- [ ] 07 — docker-compose-dev
- [ ] 08 — celery-scaffold
- [ ] 09 — webhook-enqueue

### Phase 4 — Code Understanding (0/4)
- [ ] 10 — tree-sitter-python
- [ ] 11 — diff-parser
- [ ] 12 — hunk-to-symbol
- [ ] 13 — context-expansion

### Phase 5 — Static Analysis (0/3)
- [ ] 14 — ruff-runner
- [ ] 15 — mypy-runner
- [ ] 16 — analysis-aggregator

### Phase 6 — LLM Review (0/5)
- [ ] 17 — claude-api-client
- [ ] 18 — prompt-registry
- [ ] 19 — review-agent-v1
- [ ] 20 — github-comment-poster
- [ ] 21 — style-guide-config

### Phase 7 — Observability (0/3)
- [ ] 22 — structured-logging
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

- [F02] `pydantic-settings` is the sole config source; all modules must import `get_settings()` from `app.config` — no direct `os.environ` reads anywhere in app code.

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
- [F02] `app.config.Settings` — fields: `GITHUB_APP_ID`, `GITHUB_WEBHOOK_SECRET`, `GITHUB_PRIVATE_KEY_PATH`, `CLAUDE_API_KEY` (all `str`, required); `REDIS_URL` (`str`, default `"redis://localhost:6379/0"`)
- [F02] `tests/conftest.py` — autouse fixture sets dummy env vars + clears `lru_cache` after each test; all future test files inherit this automatically

---

## Tech debt

Things left half-done, brittle, or worked around. Link to the future feature that will fix it when possible.

- _(none yet)_

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
