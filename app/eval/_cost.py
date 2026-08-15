from app.llm.cost_table import estimate_cost
from app.llm.gemini_client import GeminiClient, GeminiResponse


class _CostAccumulator:
    def __init__(self, inner: GeminiClient) -> None:
        self._inner = inner
        self._input_tokens = 0
        self._output_tokens = 0

    def complete(
        self,
        messages: list[dict],
        *,
        model: str,
        max_tokens: int,
        system: str | None = None,
    ) -> GeminiResponse:
        resp = self._inner.complete(messages, model=model, max_tokens=max_tokens, system=system)
        self._input_tokens += resp.input_tokens
        self._output_tokens += resp.output_tokens
        return resp

    def total_cost_usd(self, model: str) -> float | None:
        return estimate_cost(model, self._input_tokens, self._output_tokens)
