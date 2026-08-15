from prometheus_client import Counter, Histogram

reviews_total = Counter("reviews", "PR review tasks started")
llm_calls_total = Counter("llm_calls", "Successful Gemini API calls")
errors_total = Counter("errors", "Errors by component", ["component"])
review_duration_seconds = Histogram(
    "review_duration_seconds",
    "End-to-end review task wall-clock duration",
)
tokens_per_review = Histogram(
    "tokens_per_review",
    "Total tokens (input + output) per Gemini API call",
    buckets=[128, 512, 1024, 2048, 4096, 8192, 16384],
)
