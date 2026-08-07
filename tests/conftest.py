import pytest

from app.config import get_settings


@pytest.fixture(autouse=True)
def _set_required_env(monkeypatch):
    monkeypatch.setenv("GITHUB_APP_ID", "test-app-id")
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "test-secret")
    monkeypatch.setenv("GITHUB_PRIVATE_KEY_PATH", "/tmp/test.pem")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    yield
    get_settings.cache_clear()
