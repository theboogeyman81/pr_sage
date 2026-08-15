# Feature 21: Style Guide Config

## Goal
A YAML file defines project-specific review rules; the loader formats them into
text that gets injected into the review prompt via a new prompt version.

## In scope
- `style_guide.yaml` at project root — list of named rules with descriptions.
- `load_style_guide(path) -> str` in `app/llm/style_guide.py` — reads, validates,
  and formats the YAML as a bulleted string ready for prompt injection.
- `StyleGuideError(Exception)` — raised on missing file, unparseable YAML, or
  invalid schema (no `rules` key, wrong types).
- `prompts/review/v2.md` — replaces the existing placeholder with a real prompt
  that adds a `{style_guide}` slot alongside the existing `{diff}`, `{context}`,
  `{findings}` slots. Callers use `prompt_version=2` and pass
  `.format(diff=..., context=..., findings=..., style_guide=load_style_guide())`.
- Example rules in `style_guide.yaml`: at least 3 meaningful Python rules.
- Tests: valid load, text content, missing file, malformed YAML, missing `rules`
  key, and that `prompts/review/v2.md` contains the `{style_guide}` slot.

## Out of scope
- Per-repo or per-installation overrides of the style guide.
- Hot-reloading the YAML without restart.
- Rule severity or categories — each rule is just a name + description for now.
- Wiring `load_style_guide()` into the Celery task (that is F22+).

## File structure
```
style_guide.yaml               ← new: project-root config with example rules
app/
  llm/
    style_guide.py             ← new: StyleGuideError + load_style_guide()
prompts/
  review/
    v2.md                      ← modified: placeholder → real style-guide prompt
tests/
  test_style_guide.py          ← new
.claude/
  specs/21-style-guide-config.md
```

Files modified beyond new files:
- `app/llm/__init__.py` — export `load_style_guide`, `StyleGuideError`
- `pyproject.toml` — add `PyYAML==6.0.2`

## Contracts

```python
# app/llm/style_guide.py

from pathlib import Path
import yaml

_DEFAULT_PATH = Path(__file__).parent.parent.parent / "style_guide.yaml"


class StyleGuideError(Exception):
    """Raised when style_guide.yaml is missing, malformed, or has invalid schema."""


def load_style_guide(path: Path = _DEFAULT_PATH) -> str:
    """Read style_guide.yaml and return a formatted bullet list of rules.

    Raises StyleGuideError on missing file, bad YAML, or invalid schema.

    Output format (one rule per line):
        - <name>: <description>
        - <name>: <description>
    """
```

### `style_guide.yaml` schema
```yaml
rules:
  - name: "type-annotations"
    description: "All public functions must have type annotations on parameters and return value."
  - name: "docstrings"
    description: "All public functions and classes must have a docstring."
  - name: "no-bare-except"
    description: "Never use bare except: clauses; always catch a specific exception type."
```

### `prompts/review/v2.md` — replaces placeholder
```
You are a code reviewer. Review the following Python pull request and identify
bugs, style issues, and improvements.

Apply the following project style rules when reviewing:

## Style guide
{style_guide}

## Diff
{diff}

## Context
{context}

## Static analysis findings
{findings}

Respond with a JSON array of review comments. Each comment must have:
- "path": file path relative to the repo root
- "line": line number in the new file (integer)
- "body": comment text explaining the issue and how to fix it
- "severity": one of "error" | "warning" | "suggestion"
```

## Dependencies
- `PyYAML==6.0.2` — add to `pyproject.toml`

## Tests
Use `tmp_path` for isolation except `test_default_file_loads` and
`test_prompt_v2_has_slot` which use real files.

- `test_load_returns_string`: valid YAML with 2 rules → non-empty string
- `test_load_contains_rule_names`: output contains each rule's `name`
- `test_load_missing_file_raises`: non-existent path → `StyleGuideError`
- `test_load_malformed_yaml_raises`: file with `": bad: yaml: [` → `StyleGuideError`
- `test_load_missing_rules_key_raises`: `{}` YAML → `StyleGuideError`
- `test_default_file_loads`: `load_style_guide()` with no args succeeds on real `style_guide.yaml`
- `test_prompt_v2_has_style_guide_slot`: `PromptRegistry().get("review", 2)` contains `"{style_guide}"`

## Acceptance criteria
1. Editing a rule in `style_guide.yaml` changes the output of `load_style_guide()`.
2. `load_style_guide()` raises `StyleGuideError` on invalid input — never a raw `yaml.YAMLError` or `KeyError`.
3. `prompts/review/v2.md` contains `{style_guide}` and can be formatted with all four slots.
4. All 7 tests pass with `pytest`.
5. `PyYAML==6.0.2` pinned in `pyproject.toml`.
6. Full suite (82 existing + 7 new) stays green.
