import hashlib
import json
import time
from dataclasses import dataclass

import google.genai as genai
import structlog
from google.genai import errors as gerrors, types
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import get_settings
from app.llm.cost_table import estimate_cost
from app.llm.exceptions import LLMClientError, LLMError, LLMRateLimitError, LLMServerError

logger = structlog.get_logger()


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
        prompt_hash = hashlib.sha256(
            json.dumps(messages, sort_keys=True).encode()
        ).hexdigest()[:16]
        t0 = time.perf_counter()

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
            duration_ms = int((time.perf_counter() - t0) * 1000)
            logger.warning("llm_call", model=model, prompt_hash=prompt_hash,
                           input_tokens=None, output_tokens=None,
                           cost_usd=None, duration_ms=duration_ms, error=str(exc))
            raise LLMServerError(str(exc)) from exc
        except gerrors.ClientError as exc:
            duration_ms = int((time.perf_counter() - t0) * 1000)
            logger.warning("llm_call", model=model, prompt_hash=prompt_hash,
                           input_tokens=None, output_tokens=None,
                           cost_usd=None, duration_ms=duration_ms, error=str(exc))
            if exc.code == 429:
                raise LLMRateLimitError(str(exc)) from exc
            raise LLMClientError(str(exc)) from exc
        except Exception as exc:
            duration_ms = int((time.perf_counter() - t0) * 1000)
            logger.warning("llm_call", model=model, prompt_hash=prompt_hash,
                           input_tokens=None, output_tokens=None,
                           cost_usd=None, duration_ms=duration_ms, error=str(exc))
            raise LLMError(str(exc)) from exc

        duration_ms = int((time.perf_counter() - t0) * 1000)
        input_tokens = response.usage_metadata.prompt_token_count
        output_tokens = response.usage_metadata.candidates_token_count
        logger.info("llm_call", model=model, prompt_hash=prompt_hash,
                    input_tokens=input_tokens, output_tokens=output_tokens,
                    cost_usd=estimate_cost(model, input_tokens, output_tokens),
                    duration_ms=duration_ms)
        return GeminiResponse(
            content=response.text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
