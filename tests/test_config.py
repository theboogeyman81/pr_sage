import pytest
from pydantic_core import ValidationError

from app.config import Settings, get_settings


def test_all_required_present(monkeypatch):
    monkeypatch.setenv("REDIS_URL", "redis://custom:6380/1")
    settings = get_settings()
    assert settings.GITHUB_APP_ID == "test-app-id"
    assert settings.GITHUB_WEBHOOK_SECRET == "test-secret"
    assert settings.GITHUB_PRIVATE_KEY_PATH == "/tmp/test.pem"
    assert settings.CLAUDE_API_KEY == "test-claude-key"
    assert settings.REDIS_URL == "redis://custom:6380/1"


def test_missing_required_var(monkeypatch):
    monkeypatch.delenv("GITHUB_APP_ID", raising=False)
    get_settings.cache_clear()
    with pytest.raises(ValidationError):
        get_settings()


def test_optional_default(monkeypatch):
    monkeypatch.delenv("REDIS_URL", raising=False)
    settings = get_settings()
    assert settings.REDIS_URL == "redis://localhost:6379/0"


def test_cache():
    first = get_settings()
    second = get_settings()
    assert first is second
