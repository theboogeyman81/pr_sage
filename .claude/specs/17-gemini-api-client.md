# Feature 17: Gemini API Client

## Goal
Provide a robust, typed wrapper around the Google Gemini API so future features
can call it without caring about retry logic, error handling, or token counting.

## In scope
- `GeminiClient` class in `app/llm/gemini_client.py` that wraps `google-genai`.
- Single public method: `complete(messages, *, model, max_tokens, system) -> GeminiResponse`.
  - `messages`: `list[dict]` — each dict has `role` (`"user"` | `"model"`) and `parts: [{"text": str}]`
  - `model`: `str` (e.g. `"gemini-2.0-flash"`) — caller supplies, no default baked in
  - `max_tokens`: `int` — maps to `generation_config.max_output_tokens`
  - `system`: `str | None` — maps to `system_instruction` on the model config
- `GeminiResponse` dataclass: `content: str`, `input_tokens: int`, `output_tokens: int`.
- Typed exception hierarchy in `app/llm/exceptions.py`:
  - `LLMError` — base
  - `LLMRateLimitError(LLMError)` — 429 / resource exhausted
  - `LLMServerError(LLMError)` — 5xx / internal errors
  - `LLMClientError(LLMError)` — 4xx other than 429 (bad request, auth)
- Retry on `LLMRateLimitError` and `LLMServerError`: up to 3 attempts, exponential
  backoff (1 s, 2 s, 4 s). Implemented with `tenacity`.
- API key read from `get_settings().GEMINI_API_KEY`; client constructed once per
  `GeminiClient` instance.
- Request timeout: 60 s per attempt (passed via `httpx` or SDK transport config).
- `app/llm/__init__.py` exports `GeminiClient`, `GeminiResponse`.

## Out of scope
- Streaming responses.
- Embeddings or other Gemini endpoints.
- Multi-modal (image/audio) inputs.
- Prompt templating or registry (Feature 18).
- Caching responses.

## File structure
```
app/
  llm/
    __init__.py          ← exports GeminiClient, GeminiResponse
    gemini_client.py     ← GeminiClient, GeminiResponse
    exceptions.py        ← LLMError hierarchy
tests/
  test_gemini_client.py  ← unit tests (mocked SDK)
.claude/
  specs/17-gemini-api-client.md
```

No changes to existing files except `pyproject.toml` (new deps).

## Contracts

```python
# app/llm/exceptions.py
class LLMError(Exception): ...
class LLMRateLimitError(LLMError): ...
class LLMServerError(LLMError): ...
class LLMClientError(LLMError): ...

# app/llm/gemini_client.py
from dataclasses import dataclass
from app.llm.exceptions import LLMError, LLMRateLimitError, LLMServerError, LLMClientError

@dataclass(frozen=True)
class GeminiResponse:
    content: str
    input_tokens: int
    output_tokens: int

class GeminiClient:
    def __init__(self) -> None:
        # reads GEMINI_API_KEY from get_settings(), constructs sdk client
        ...

    def complete(
        self,
        messages: list[dict],
        *,
        model: str,
        max_tokens: int,
        system: str | None = None,
    ) -> GeminiResponse:
        # retries on rate-limit / server errors, raises typed LLMError on failure
        ...
```

### SDK usage pattern
```python
import google.genai as genai
from google.genai import types

client = genai.Client(api_key=api_key)
response = client.models.generate_content(
    model=model,
    contents=messages,           # list[dict] with role/parts
    config=types.GenerateContentConfig(
        system_instruction=system,
        max_output_tokens=max_tokens,
    ),
)
content = response.text
input_tokens = response.usage_metadata.prompt_token_count
output_tokens = response.usage_metadata.candidates_token_count
```

### Error mapping
`google-genai` uses its own exception hierarchy (`google.genai.errors`), not `google.api_core`:

| SDK exception | Condition | Typed exception |
|---|---|---|
| `google.genai.errors.ClientError` | `exc.code == 429` | `LLMRateLimitError` |
| `google.genai.errors.ClientError` | other 4xx | `LLMClientError` |
| `google.genai.errors.ServerError` | any 5xx | `LLMServerError` |
| any other exception from SDK | — | `LLMError` (re-wrapped) |

## Dependencies
- `google-genai==1.16.1`
- `tenacity==9.1.2`

(Both to be added to `pyproject.toml`.)

## Tests
All tests mock the SDK client — no real API calls.

- `test_complete_success`: mock SDK returns valid response → `GeminiResponse` with correct fields
- `test_complete_returns_tokens`: `input_tokens` and `output_tokens` come from `usage_metadata`
- `test_rate_limit_retries_then_succeeds`: first two calls raise `ResourceExhausted`, third succeeds → single `GeminiResponse` returned
- `test_rate_limit_exhausted_raises`: all 3 attempts raise `ResourceExhausted` → `LLMRateLimitError` propagates
- `test_server_error_retries`: `InternalServerError` triggers retry same as rate limit
- `test_client_error_no_retry`: `InvalidArgument` raises `LLMClientError` immediately (no retry)
- `test_system_instruction_passed`: `system` arg is forwarded to `GenerateContentConfig.system_instruction`
- `test_no_system_instruction`: `system=None` → `system_instruction` omitted / `None` in config

## Acceptance criteria
1. `GeminiClient().complete(...)` returns a `GeminiResponse` with correct `content`, `input_tokens`, `output_tokens`.
2. `LLMRateLimitError` / `LLMServerError` trigger up to 3 attempts; `LLMClientError` does not retry.
3. After 3 failed attempts the appropriate typed `LLMError` subclass propagates to the caller.
4. All 8 tests pass with `pytest`.
5. `google-genai` and `tenacity` are pinned in `pyproject.toml`.
6. Full suite (all existing + 8 new tests) stays green.
