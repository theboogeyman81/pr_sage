from pathlib import Path

import pytest

from app.llm.prompt_registry import PromptRegistry
from app.llm.style_guide import StyleGuideError, load_style_guide

_VALID_YAML = """\
rules:
  - name: "type-annotations"
    description: "Add type annotations."
  - name: "docstrings"
    description: "Add docstrings."
"""


def test_load_returns_string(tmp_path):
    p = tmp_path / "sg.yaml"
    p.write_text(_VALID_YAML, encoding="utf-8")
    result = load_style_guide(p)
    assert isinstance(result, str) and len(result) > 0


def test_load_contains_rule_names(tmp_path):
    p = tmp_path / "sg.yaml"
    p.write_text(_VALID_YAML, encoding="utf-8")
    result = load_style_guide(p)
    assert "type-annotations" in result
    assert "docstrings" in result


def test_load_missing_file_raises(tmp_path):
    with pytest.raises(StyleGuideError):
        load_style_guide(tmp_path / "nonexistent.yaml")


def test_load_malformed_yaml_raises(tmp_path):
    p = tmp_path / "sg.yaml"
    p.write_text(": bad: yaml: [", encoding="utf-8")
    with pytest.raises(StyleGuideError):
        load_style_guide(p)


def test_load_missing_rules_key_raises(tmp_path):
    p = tmp_path / "sg.yaml"
    p.write_text("{}", encoding="utf-8")
    with pytest.raises(StyleGuideError):
        load_style_guide(p)


def test_default_file_loads():
    result = load_style_guide()
    assert isinstance(result, str) and len(result) > 0


def test_prompt_v2_has_style_guide_slot():
    text = PromptRegistry().get("review", 2)
    assert "{style_guide}" in text
