COST_PER_TOKEN: dict[str, dict[str, float]] = {
    "gemini-2.0-flash": {"input": 0.10 / 1_000_000, "output": 0.40 / 1_000_000},
    "gemini-1.5-flash": {"input": 0.075 / 1_000_000, "output": 0.30 / 1_000_000},
    "gemini-1.5-pro":   {"input": 1.25 / 1_000_000, "output": 5.00 / 1_000_000},
}


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float | None:
    rates = COST_PER_TOKEN.get(model)
    if rates is None:
        return None
    return round(input_tokens * rates["input"] + output_tokens * rates["output"], 6)
