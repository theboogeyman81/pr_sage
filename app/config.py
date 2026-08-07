from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    GITHUB_APP_ID: str
    GITHUB_WEBHOOK_SECRET: str
    GITHUB_PRIVATE_KEY_PATH: str
    GEMINI_API_KEY: str
    REDIS_URL: str = "redis://localhost:6379/0"


@lru_cache
def get_settings() -> Settings:
    return Settings()
