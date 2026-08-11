import pytest
import structlog
from unittest.mock import MagicMock, patch
from google.genai import errors as gerrors

from app.llm.gemini_client import GeminiClient
from app.llm.cost_table import estimate_cost

_MODEL = "gemini-2.0-flash"
_MESSAGES = [{"role": "user", "parts": [{"text": "hello"}]}]
_OTHER_MESSAGES = [{"role": "user", "parts": [{"text": "different"}]}]


def _make_response(input_tokens=10, output_tokens=5):
    resp = MagicMock()
    resp.text = "ok"
    resp.usage_metadata.prompt_token_count = input_tokens
    resp.usage_metadata.candidates_token_count = output_tokens
    return resp


def _server_error() -> gerrors.ServerError:
    return gerrors.ServerError(500, {"error": {"code": 500, "message": "boom", "status": "INTERNAL"}})


@pytest.fixture()
def client_and_mock():
    with patch("app.llm.gemini_client.genai.Client") as MockClient:
        mock_sdk = MockClient.return_value
        yield GeminiClient(), mock_sdk


def test_trace_log_on_success(client_and_mock):
    client, mock_sdk = client_and_mock
    mock_sdk.models.generate_content.return_value = _make_response(input_tokens=10, output_tokens=5)
    with structlog.testing.capture_logs() as logs:
        client.complete(_MESSAGES, model=_MODEL, max_tokens=100)
    assert len(logs) == 1
    log = logs[0]
    assert log["event"] == "llm_call"
    assert log["log_level"] == "info"
    assert log["model"] == _MODEL
    assert isinstance(log["prompt_hash"], str) and len(log["prompt_hash"]) == 16
    assert log["input_tokens"] == 10
    assert log["output_tokens"] == 5
    assert isinstance(log["cost_usd"], float)
    assert isinstance(log["duration_ms"], int) and log["duration_ms"] >= 0


def test_trace_log_on_error(client_and_mock):
    client, mock_sdk = client_and_mock
    mock_sdk.models.generate_content.side_effect = _server_error()
    with structlog.testing.capture_logs() as logs:
        with pytest.raises(Exception):
            client.complete(_MESSAGES, model=_MODEL, max_tokens=100)
    warning_logs = [l for l in logs if l["log_level"] == "warning"]
    assert len(warning_logs) >= 1
    log = warning_logs[0]
    assert log["event"] == "llm_call"
    assert "error" in log


def test_estimate_cost_known_model():
    result = estimate_cost("gemini-2.0-flash", 1_000_000, 1_000_000)
    assert result == pytest.approx(0.50, rel=1e-6)


def test_estimate_cost_unknown_model():
    assert estimate_cost("unknown-model-xyz", 100, 100) is None


def test_prompt_hash_is_deterministic(client_and_mock):
    client, mock_sdk = client_and_mock
    mock_sdk.models.generate_content.return_value = _make_response()
    with structlog.testing.capture_logs() as logs1:
        client.complete(_MESSAGES, model=_MODEL, max_tokens=100)
    with structlog.testing.capture_logs() as logs2:
        client.complete(_MESSAGES, model=_MODEL, max_tokens=100)
    assert logs1[0]["prompt_hash"] == logs2[0]["prompt_hash"]


def test_prompt_hash_changes_with_input(client_and_mock):
    client, mock_sdk = client_and_mock
    mock_sdk.models.generate_content.return_value = _make_response()
    with structlog.testing.capture_logs() as logs1:
        client.complete(_MESSAGES, model=_MODEL, max_tokens=100)
    with structlog.testing.capture_logs() as logs2:
        client.complete(_OTHER_MESSAGES, model=_MODEL, max_tokens=100)
    assert logs1[0]["prompt_hash"] != logs2[0]["prompt_hash"]
