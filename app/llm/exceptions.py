class LLMError(Exception):
    """Base class for all LLM API errors raised by this project."""


class LLMRateLimitError(LLMError):
    """Raised on 429 / ResourceExhausted responses."""


class LLMServerError(LLMError):
    """Raised on 5xx / InternalServerError or ServiceUnavailable responses."""


class LLMClientError(LLMError):
    """Raised on 4xx responses other than 429 (bad request, auth failure, etc.)."""
