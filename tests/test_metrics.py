import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from google.genai import errors as gerrors
from prometheus_client import REGISTRY

from app.main import app
from app.llm.gemini_client import GeminiClient

client = TestClient(app)

_MODEL = "gemini-2.0-flash"
_MESSAGES = [{"role": "user", "parts": [{"text": "hello"}]}]


def _make_response(input_tokens=10, output_tokens=5):
    resp = MagicMock()
    resp.text = "ok"
    resp.usage_metadata.prompt_token_count = input_tokens
    resp.usage_metadata.candidates_token_count = output_tokens
    return resp


def _server_error() -> gerrors.ServerError:
    return gerrors.ServerError(500, {"error": {"code": 500, "message": "boom", "status": "INTERNAL"}})


def test_metrics_endpoint_returns_200():
    response = client.get("/metrics")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")


def test_metrics_endpoint_contains_all_metric_names():
    response = client.get("/metrics")
    body = response.text
    assert "reviews_total" in body
    assert "llm_calls_total" in body
    assert "errors_total" in body
    assert "review_duration_seconds" in body
    assert "tokens_per_review" in body


def test_llm_calls_total_increments():
    before = REGISTRY.get_sample_value("llm_calls_total") or 0.0
    with patch("app.llm.gemini_client.genai.Client") as MockClient:
        mock_sdk = MockClient.return_value
        mock_sdk.models.generate_content.return_value = _make_response()
        gc = GeminiClient()
        gc.complete(_MESSAGES, model=_MODEL, max_tokens=100)
    after = REGISTRY.get_sample_value("llm_calls_total") or 0.0
    assert after == before + 1


def test_tokens_per_review_observed():
    before_sum = REGISTRY.get_sample_value("tokens_per_review_sum") or 0.0
    with patch("app.llm.gemini_client.genai.Client") as MockClient:
        mock_sdk = MockClient.return_value
        mock_sdk.models.generate_content.return_value = _make_response(input_tokens=10, output_tokens=5)
        gc = GeminiClient()
        gc.complete(_MESSAGES, model=_MODEL, max_tokens=100)
    after_sum = REGISTRY.get_sample_value("tokens_per_review_sum") or 0.0
    assert after_sum == before_sum + 15


def test_errors_total_increments_on_llm_error():
    label = {"component": "llm"}
    before = REGISTRY.get_sample_value("errors_total", label) or 0.0
    with patch("app.llm.gemini_client.genai.Client") as MockClient:
        mock_sdk = MockClient.return_value
        mock_sdk.models.generate_content.side_effect = _server_error()
        gc = GeminiClient()
        with pytest.raises(Exception):
            gc.complete(_MESSAGES, model=_MODEL, max_tokens=100)
    after = REGISTRY.get_sample_value("errors_total", label) or 0.0
    assert after >= before + 1
