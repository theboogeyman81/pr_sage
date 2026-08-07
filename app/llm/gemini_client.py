from dataclasses import dataclass

import google.genai as genai
from google.genai import errors as gerrors, types
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import get_settings
from app.llm.exceptions import LLMClientError, LLMError, LLMRateLimitError, LLMServerError


@dataclass(frozen=True)
class GeminiResponse:
    content: str
    input_tokens: int
    output_tokens: int


class GeminiClient:
    def __init__(self) -> None:
        self._client = genai.Client(api_key=get_settings().GEMINI_API_KEY)

    def complete(
        self,
        messages: list[dict],
        *,
        model: str,
        max_tokens: int,
        system: str | None = None,
    ) -> GeminiResponse:
        return self._call(messages, model=model, max_tokens=max_tokens, system=system)

    @retry(
        retry=retry_if_exception_type((LLMRateLimitError, LLMServerError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        reraise=True,
    )
    def _call(
        self,
        messages: list[dict],
        *,
        model: str,
        max_tokens: int,
        system: str | None,
    ) -> GeminiResponse:
        try:
            response = self._client.models.generate_content(
                model=model,
                contents=messages,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    max_output_tokens=max_tokens,
                ),
            )
        except gerrors.ServerError as exc:
            raise LLMServerError(str(exc)) from exc
        except gerrors.ClientError as exc:
            if exc.code == 429:
                raise LLMRateLimitError(str(exc)) from exc
            raise LLMClientError(str(exc)) from exc
        except Exception as exc:
            raise LLMError(str(exc)) from exc

        return GeminiResponse(
            content=response.text,
            input_tokens=response.usage_metadata.prompt_token_count,
            output_tokens=response.usage_metadata.candidates_token_count,
        )
