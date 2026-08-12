# LEARNINGS.md

One entry per merged feature. Minimum: one surprise + one decision.

---

## Feature 02 — config-management

**Surprise:** `lru_cache` on `get_settings()` bleeds across tests — a test that monkeypatches env vars and calls `get_settings()` will poison the cache for every subsequent test. Required an explicit `get_settings.cache_clear()` call in the conftest teardown. Easy to miss and produces hard-to-debug flakiness (tests pass in isolation, fail in a full suite run depending on order).

**Decision:** Put the autouse env-var fixture in `tests/conftest.py` rather than duplicating it per test file. This means every future test module (including `test_health.py`) automatically gets the required vars without any extra setup. The tradeoff is that `conftest.py` becomes load-bearing infrastructure — if someone removes the autouse fixture, many unrelated tests will break.

---

## Feature 11 — diff-parser

**Surprise:** The `@@` hunk header can omit the count when it is `1` (e.g. `@@ -5 +5 @@` means one line changed). The `(?:,(\d+))?` optional group handles this — when the group is absent `m.group(2)` is `None`, not `"0"`. Using `int(m.group(2) or 1)` correctly defaults to `1`. Critically, `"0"` is a truthy non-empty string in Python, so an explicit count of `0` (new-file hunks: `@@ -0,0 +1,3 @@`) is preserved correctly and is not replaced by `1`.

**Decision:** Used a lookahead regex split (`re.split(r'(?=^diff --git )', ...)`) rather than splitting on the literal string and losing the header. This keeps each section self-contained so `_parse_section` can detect skippable cases (binary, rename) without needing extra context from the caller. The deleted-file path (`+++ /dev/null`) is resolved by falling back to `old_path` from `--- a/<path>` after the path-extraction loop.
