import pytest

from app.llm.exceptions import PromptNotFoundError
from app.llm.prompt_registry import PromptRegistry


def _registry(tmp_path):
    return PromptRegistry(root=tmp_path)


def test_get_returns_content(tmp_path):
    (tmp_path / "greet").mkdir()
    (tmp_path / "greet" / "v1.md").write_text("hello {name}", encoding="utf-8")
    assert _registry(tmp_path).get("greet", 1) == "hello {name}"


def test_get_missing_name_raises(tmp_path):
    with pytest.raises(PromptNotFoundError):
        _registry(tmp_path).get("nonexistent", 1)


def test_get_missing_version_raises(tmp_path):
    (tmp_path / "greet").mkdir()
    (tmp_path / "greet" / "v1.md").write_text("hello", encoding="utf-8")
    with pytest.raises(PromptNotFoundError):
        _registry(tmp_path).get("greet", 99)


def test_get_version_routing(tmp_path):
    (tmp_path / "review").mkdir()
    (tmp_path / "review" / "v1.md").write_text("version one", encoding="utf-8")
    (tmp_path / "review" / "v2.md").write_text("version two", encoding="utf-8")
    assert _registry(tmp_path).get("review", 2) == "version two"


def test_seed_prompts_loadable():
    registry = PromptRegistry()
    v1 = registry.get("review", 1)
    v2 = registry.get("review", 2)
    assert "{diff}" in v1
    assert len(v2) > 0
