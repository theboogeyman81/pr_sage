# LEARNINGS.md

One entry per merged feature. Minimum: one surprise + one decision.

---

## Feature 02 — config-management

**Surprise:** `lru_cache` on `get_settings()` bleeds across tests — a test that monkeypatches env vars and calls `get_settings()` will poison the cache for every subsequent test. Required an explicit `get_settings.cache_clear()` call in the conftest teardown. Easy to miss and produces hard-to-debug flakiness (tests pass in isolation, fail in a full suite run depending on order).

**Decision:** Put the autouse env-var fixture in `tests/conftest.py` rather than duplicating it per test file. This means every future test module (including `test_health.py`) automatically gets the required vars without any extra setup. The tradeoff is that `conftest.py` becomes load-bearing infrastructure — if someone removes the autouse fixture, many unrelated tests will break.
