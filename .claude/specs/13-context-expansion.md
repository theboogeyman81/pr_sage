# Feature 13: Context Expansion

## Goal
Given a touched symbol and its file location at a specific commit SHA, fetch the full symbol body plus N surrounding lines from the GitHub API, with per-file caching to avoid redundant fetches.

## In scope
- `expand_context(repo, sha, path, symbol, *, auth, padding=10) -> str` — fetches the file at `(repo, sha, path)` via GitHub Contents API, slices from `max(0, symbol.start_line - 1 - padding)` to `min(len(lines), symbol.end_line + padding)`, returns the slice as a single string.
- Per-`(sha, path)` in-memory cache on the `ContextExpander` class so the same file is not fetched twice in one review pass.
- `ContextExpander(auth: GitHubAppAuth)` — class that owns the cache and exposes `expand_context(...)`.
- Typed exception `FileNotFoundAtSHA` (subclass of `GitHubAPIError`) for 404s on the file fetch.
- Tests with mocked HTTP: cache hit, cache miss, 404 path, padding clamped at file boundaries.

## Out of scope
- Cross-file context (imports, call graph).
- Persistent cache (Redis, disk) — in-memory per instance only.
- Fetching entire directories.
- Languages other than Python (the slice is line-based and language-agnostic, but the caller always passes Python symbols for v1).

## File structure
```
app/
  github/
    context.py          ← new: ContextExpander class + expand_context logic
    exceptions.py       ← modified: add FileNotFoundAtSHA
tests/
  test_context_expansion.py   ← new
.claude/
  specs/13-context-expansion.md   ← this file
```

## Contracts

```python
# app/github/context.py

class ContextExpander:
    def __init__(self, auth: GitHubAppAuth) -> None: ...

    def expand_context(
        self,
        repo: str,           # "owner/repo"
        sha: str,            # full 40-char commit SHA
        path: str,           # file path within the repo, e.g. "app/main.py"
        symbol: Symbol,      # from app.parser.python.Symbol
        *,
        padding: int = 10,
    ) -> str:
        # Returns the sliced file content as a string (lines joined with "\n").
        # Raises FileNotFoundAtSHA if GitHub returns 404.
        # Raises GitHubServerError on 5xx.
        ...
```

```python
# app/github/exceptions.py (addition)
class FileNotFoundAtSHA(GitHubAPIError): ...
```

GitHub Contents API endpoint used:
```
GET https://api.github.com/repos/{repo}/contents/{path}?ref={sha}
Accept: application/vnd.github.raw+json
Authorization: Bearer {installation_token}
```
Response is the raw file text when the `Accept` header requests raw content.

## Dependencies
No new packages — uses `httpx` (already pinned) for the GitHub API call.

## Tests
- `test_expand_context_fetches_and_slices`: mocked GET returns a 20-line file; asserts the returned string covers symbol lines ± padding, clamped at boundaries.
- `test_expand_context_cache_hit`: two calls with the same `(sha, path)` result in only one HTTP request.
- `test_expand_context_cache_miss_different_sha`: two calls with different SHAs each trigger a separate HTTP request.
- `test_expand_context_404_raises`: mocked 404 raises `FileNotFoundAtSHA`.
- `test_expand_context_padding_clamped`: symbol near top of file — start slice never goes below line 0.

## Acceptance criteria
1. `expand_context` returns the correct line slice (symbol body + padding) for a fixture file.
2. A second call for the same `(sha, path)` does not make a second HTTP request (cache hit verified via mock call count).
3. A 404 from GitHub raises `FileNotFoundAtSHA`, not an untyped exception.
4. All 5 tests pass with `pytest`.
5. No new unpinned dependencies added to `pyproject.toml`.
