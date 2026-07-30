# Feature 02: config-management

## Goal
Centralized, validated configuration loaded from environment variables via `pydantic-settings`, failing fast on any missing required var.

## In scope
- `app/config.py` — `Settings` class with all required and optional fields
- Fields: `GITHUB_APP_ID` (required), `GITHUB_WEBHOOK_SECRET` (required), `GITHUB_PRIVATE_KEY_PATH` (required), `CLAUDE_API_KEY` (required), `REDIS_URL` (optional, default `redis://localhost:6379/0`)
- `Settings` loaded once at import time via a module-level `get_settings()` function cached with `functools.lru_cache`
- `app/main.py` updated to call `get_settings()` at startup (proves fail-fast boot behaviour)
- `.env.example` updated to include all five vars
- Tests covering: all required vars present → settings load; one required var missing → `ValidationError` raised; optional var absent → default used; `lru_cache` means second call returns the same object

## Out of scope
- Actually using any settings value in business logic (that's each downstream feature's job)
- Loading from a `.env` file at runtime (dev loads env vars via shell or an `.env` loader outside the app)
- Secret rotation or vault integration

## File structure
```
app/
  config.py          # new — Settings class + get_settings()
  main.py            # modified — call get_settings() at startup
tests/
  test_config.py     # new — four tests listed above
pyproject.toml       # modified — add pydantic-settings==2.7.0
.env.example         # modified — add CLAUDE_API_KEY, REDIS_URL
```

## Contracts

```python
# app/config.py
from functools import lru_cache
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    GITHUB_APP_ID: str
    GITHUB_WEBHOOK_SECRET: str
    GITHUB_PRIVATE_KEY_PATH: str
    CLAUDE_API_KEY: str
    REDIS_URL: str = "redis://localhost:6379/0"

@lru_cache
def get_settings() -> Settings:
    ...
```

## Dependencies
- `pydantic-settings==2.7.0`

## Tests
- `test_all_required_present`: monkeypatches all five env vars → `get_settings()` returns a `Settings` instance with correct values
- `test_missing_required_var`: monkeypatches only four of the five required vars → importing/calling `get_settings()` raises `pydantic_core.ValidationError`
- `test_optional_default`: omits `REDIS_URL` → `settings.REDIS_URL == "redis://localhost:6379/0"`
- `test_cache`: calls `get_settings()` twice → both calls return the identical object (`is` check)

## Acceptance criteria
1. App fails to boot with a clear `ValidationError` if any required env var is missing
2. App boots normally when all required vars are set
3. All four tests pass (`pytest tests/test_config.py`)
4. `get_settings()` is the single import used by any other module that needs config — no direct `os.environ` reads elsewhere
