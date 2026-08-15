# Feature 18: Prompt Registry

## Goal
Load versioned prompt files by name and version so that call sites never
embed raw prompt strings in Python code.

## In scope
- `prompts/<name>/v<N>.md` directory layout — one directory per prompt name,
  one file per version.
- `PromptRegistry` class in `app/llm/prompt_registry.py` with a single method
  `get(name: str, version: int) -> str` that reads and returns the file contents.
- Version must be explicit at every call site — no `"latest"` shortcut.
- Registry resolves paths relative to the project root (where `prompts/` lives),
  not relative to `app/`.
- Raises `PromptNotFoundError` (subclass of `LLMError`) when the file does not exist.
- Two seed prompt files committed under `prompts/` to satisfy tests (e.g.
  `prompts/review/v1.md` and `prompts/review/v2.md`).
- Tests cover: valid load, missing name, missing version, wrong type for version.

## Out of scope
- Templating language — callers use Python `.format()` or f-strings on the
  returned string.
- Hot-reload / watching files for changes.
- Caching (file reads are cheap; adds complexity for no gain at this scale).
- Per-repo or per-installation prompt overrides.

## File structure
```
prompts/
  review/
    v1.md          ← seed prompt (placeholder review instructions)
    v2.md          ← seed prompt (second version for testing)
app/
  llm/
    prompt_registry.py   ← PromptRegistry + PromptNotFoundError
tests/
  test_prompt_registry.py
.claude/
  specs/18-prompt-registry.md
```

No changes to existing files except `app/llm/exceptions.py` (add
`PromptNotFoundError`).

## Contracts

```python
# app/llm/exceptions.py  (addition)
class PromptNotFoundError(LLMError):
    """Raised when the requested prompt name/version file does not exist."""

# app/llm/prompt_registry.py
from pathlib import Path

_PROMPTS_ROOT = Path(__file__).parent.parent.parent / "prompts"

class PromptRegistry:
    def __init__(self, root: Path = _PROMPTS_ROOT) -> None:
        """Accept an optional root for test isolation."""
        self._root = root

    def get(self, name: str, version: int) -> str:
        """Return the prompt text for prompts/<name>/v<version>.md.

        Raises PromptNotFoundError if the file does not exist.
        """
        path = self._root / name / f"v{version}.md"
        if not path.exists():
            raise PromptNotFoundError(f"Prompt not found: {name}/v{version}")
        return path.read_text(encoding="utf-8")
```

`app/llm/__init__.py` exports updated to include `PromptRegistry` and
`PromptNotFoundError`.

## Dependencies
None. Uses only `pathlib` from the stdlib.

## Tests
Tests use a `tmp_path`-based registry (pytest's built-in fixture) so they
never touch the real `prompts/` directory.

- `test_get_returns_content`: write a file at `tmp_path/greet/v1.md` → `registry.get("greet", 1)` returns its text
- `test_get_missing_name_raises`: `registry.get("nonexistent", 1)` → `PromptNotFoundError`
- `test_get_missing_version_raises`: name dir exists but `v99.md` does not → `PromptNotFoundError`
- `test_get_version_is_integer`: version `2` loads `v2.md`, not `v1.md`
- `test_seed_prompts_loadable`: instantiate `PromptRegistry()` (real root) and call `get("review", 1)` and `get("review", 2)` — both succeed without error

## Acceptance criteria
1. `PromptRegistry().get("review", 1)` returns the contents of `prompts/review/v1.md`.
2. `PromptRegistry().get("review", 99)` raises `PromptNotFoundError`.
3. All 5 tests pass with `pytest`.
4. No new dependencies added to `pyproject.toml`.
5. Full suite (64 existing + 5 new) stays green.
