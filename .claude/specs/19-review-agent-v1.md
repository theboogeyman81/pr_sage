# Feature 19: Review Agent v1

## Goal
Given a diff, expanded context, and static-analysis findings, call the Gemini
API with a versioned prompt and return a validated list of structured review
comments.

## In scope
- `Comment` Pydantic model: `path: str`, `line: int`, `body: str`,
  `severity: Literal["error", "warning", "suggestion"]`.
- `ReviewError(LLMError)` — raised when the model response cannot be parsed as
  JSON or fails Pydantic validation.
- `run_review(diff, context, findings, *, client, registry, model, prompt_version) -> list[Comment]`
  in `app/llm/review_agent.py`. **Pratham implements the body** (agent loop,
  prompt formatting, response parsing) per CLAUDE.md §3.
- Claude Code scaffolds the full module: imports, `Comment`, `ReviewError`, the
  function signature with type annotations, and a docstring describing the
  expected call flow. The body is left as a stub (`raise NotImplementedError`).
- Tests over a fixture diff with a mocked `GeminiClient` that returns
  valid JSON, invalid JSON, and schema-valid-but-wrong-type JSON — verifying
  that the contract (return shape + error path) is clear even before the body
  is implemented.

## Out of scope
- Multi-turn agent, tool use, streaming.
- Wiring `run_review` into the Celery task (`review_pr`) — that is Feature 20+.
- Prompt engineering decisions — Pratham owns those.
- Truncation or chunking of very large diffs/context.

## File structure
```
app/
  llm/
    review_agent.py     ← new: Comment, ReviewError, run_review (stub)
tests/
  test_review_agent.py  ← new: contract tests (mocked GeminiClient)
.claude/
  specs/19-review-agent-v1.md
```

Existing files modified:
- `app/llm/exceptions.py` — append `ReviewError(LLMError)`
- `app/llm/__init__.py` — export `Comment`, `ReviewError`, `run_review`

## Contracts

```python
# app/llm/exceptions.py (addition)
class ReviewError(LLMError):
    """Raised when the model response is not valid JSON or fails Comment validation."""

# app/llm/review_agent.py
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, ValidationError

from app.analysis.finding import Finding
from app.llm.exceptions import ReviewError
from app.llm.gemini_client import GeminiClient
from app.llm.prompt_registry import PromptRegistry


class Comment(BaseModel):
    path: str
    line: int
    body: str
    severity: Literal["error", "warning", "suggestion"]


def run_review(
    diff: str,
    context: str,
    findings: list[Finding],
    *,
    client: GeminiClient,
    registry: PromptRegistry,
    model: str,
    prompt_version: int = 1,
) -> list[Comment]:
    """Call Gemini with the review prompt and return validated Comments.

    Expected call flow (Pratham implements):
    1. Load prompt template: registry.get("review", prompt_version)
    2. Serialize findings to a human-readable string
    3. Format the template with diff, context, and findings text
    4. Call client.complete(messages, model=model, max_tokens=...)
    5. Parse response.content as JSON → list of dicts
    6. Validate each dict as Comment; raise ReviewError on failure
    7. Return list[Comment]
    """
    raise NotImplementedError
```

`app/llm/__init__.py` exports updated to include `Comment`, `ReviewError`,
`run_review`.

## Dependencies
None new. `pydantic` is already installed transitively via `pydantic-settings`.

## Tests
Tests mock `GeminiClient` at the `app.llm.review_agent.GeminiClient` boundary.
Because the body is a stub, the tests are **contract tests** — they describe the
expected behavior so Pratham can implement against them. They will fail until
the body is filled in; that is intentional and expected.

- `test_comment_model_valid` — `Comment(path="a.py", line=1, body="x", severity="error")` constructs without error
- `test_comment_model_rejects_bad_severity` — `severity="critical"` raises `pydantic.ValidationError`
- `test_review_error_is_llm_error` — `ReviewError` is a subclass of `LLMError`

(Integration tests that exercise `run_review` end-to-end are deferred until
Pratham fills in the body. The three model tests above verify the data schema
independently of the agent loop.)

## Acceptance criteria
1. `Comment` model accepts valid severity values and rejects invalid ones.
2. `ReviewError` is importable from `app.llm` and is a subclass of `LLMError`.
3. `run_review` is importable with the correct signature (type-checker safe).
4. All 3 tests pass with `pytest`.
5. No new dependencies added to `pyproject.toml`.
6. Full suite (69 existing + 3 new) stays green.
7. Pratham can implement the body and the end-to-end tests pass against the
   acceptance criteria: fixture diff → valid `list[Comment]` · malformed JSON →
   `ReviewError`.
