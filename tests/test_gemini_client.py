from unittest.mock import MagicMock, patch

import pytest
from google.genai import errors as gerrors

from app.llm.exceptions import LLMClientError, LLMRateLimitError, LLMServerError
from app.llm.gemini_client import GeminiClient, GeminiResponse

_MODEL = "gemini-2.0-flash"
_MESSAGES = [{"role": "user", "parts": [{"text": "hello"}]}]


def _make_response(text="ok", input_tokens=10, output_tokens=5):
    resp = MagicMock()
    resp.text = text
    resp.usage_metadata.prompt_token_count = input_tokens
    resp.usage_metadata.candidates_token_count = output_tokens
    return resp


def _client_error(code: int) -> gerrors.ClientError:
    return gerrors.ClientError(code, {"error": {"code": code, "message": "err", "status": "ERR"}})


def _server_error() -> gerrors.ServerError:
    return gerrors.ServerError(500, {"error": {"code": 500, "message": "boom", "status": "INTERNAL"}})


@pytest.fixture()
def client_and_mock():
    with patch("app.llm.gemini_client.genai.Client") as MockClient:
        mock_sdk = MockClient.return_value
        yield GeminiClient(), mock_sdk


def test_complete_success(client_and_mock):
    client, mock_sdk = client_and_mock
    mock_sdk.models.generate_content.return_value = _make_response("hello back")
    result = client.complete(_MESSAGES, model=_MODEL, max_tokens=100)
    assert isinstance(result, GeminiResponse)
    assert result.content == "hello back"


def test_complete_returns_tokens(client_and_mock):
    client, mock_sdk = client_and_mock
    mock_sdk.models.generate_content.return_value = _make_response(
        input_tokens=42, output_tokens=17
    )
    result = client.complete(_MESSAGES, model=_MODEL, max_tokens=100)
    assert result.input_tokens == 42
    assert result.output_tokens == 17


def test_rate_limit_retries_then_succeeds(client_and_mock):
    client, mock_sdk = client_and_mock
    mock_sdk.models.generate_content.side_effect = [
        _client_error(429),
        _client_error(429),
        _make_response("finally"),
    ]
    result = client.complete(_MESSAGES, model=_MODEL, max_tokens=100)
    assert result.content == "finally"
    assert mock_sdk.models.generate_content.call_count == 3


def test_rate_limit_exhausted_raises(client_and_mock):
    client, mock_sdk = client_and_mock
    mock_sdk.models.generate_content.side_effect = _client_error(429)
    with pytest.raises(LLMRateLimitError):
        client.complete(_MESSAGES, model=_MODEL, max_tokens=100)
    assert mock_sdk.models.generate_content.call_count == 3


def test_server_error_retries(client_and_mock):
    client, mock_sdk = client_and_mock
    mock_sdk.models.generate_content.side_effect = _server_error()
    with pytest.raises(LLMServerError):
        client.complete(_MESSAGES, model=_MODEL, max_tokens=100)
    assert mock_sdk.models.generate_content.call_count == 3


def test_client_error_no_retry(client_and_mock):
    client, mock_sdk = client_and_mock
    mock_sdk.models.generate_content.side_effect = _client_error(400)
    with pytest.raises(LLMClientError):
        client.complete(_MESSAGES, model=_MODEL, max_tokens=100)
    assert mock_sdk.models.generate_content.call_count == 1


def test_system_instruction_passed(client_and_mock):
    client, mock_sdk = client_and_mock
    mock_sdk.models.generate_content.return_value = _make_response()
    client.complete(_MESSAGES, model=_MODEL, max_tokens=50, system="be terse")
    _, kwargs = mock_sdk.models.generate_content.call_args
    assert kwargs["config"].system_instruction == "be terse"


def test_no_system_instruction(client_and_mock):
    client, mock_sdk = client_and_mock
    mock_sdk.models.generate_content.return_value = _make_response()
    client.complete(_MESSAGES, model=_MODEL, max_tokens=50)
    _, kwargs = mock_sdk.models.generate_content.call_args
    assert kwargs["config"].system_instruction is None
