import json
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from app.llm.exceptions import LLMError, ReviewError
from app.llm.gemini_client import GeminiClient, GeminiResponse
from app.llm.prompt_registry import PromptRegistry
from app.llm.review_agent import Comment, run_review

_DIFF = "diff --git a/app/foo.py b/app/foo.py\n+def foo(): pass\n"
_CONTEXT = "def foo(): pass"
_FINDINGS = []
_MODEL = "gemini-2.0-flash"
_REGISTRY = PromptRegistry()

_VALID_COMMENT = {
    "path": "app/foo.py",
    "line": 1,
    "body": "Missing docstring.",
    "severity": "suggestion",
}


def _mock_client(content: str) -> GeminiClient:
    client = MagicMock(spec=GeminiClient)
    client.complete.return_value = GeminiResponse(
        content=content, input_tokens=10, output_tokens=20
    )
    return client


def test_comment_valid():
    c = Comment(path="a.py", line=1, body="x", severity="error")
    assert c.severity == "error"


def test_comment_bad_severity():
    with pytest.raises(ValidationError):
        Comment(path="a.py", line=1, body="x", severity="critical")


def test_review_error_is_llm_error():
    assert isinstance(ReviewError("boom"), LLMError)


def test_run_review_success():
    client = _mock_client(json.dumps([_VALID_COMMENT]))
    comments = run_review(_DIFF, _CONTEXT, _FINDINGS, client=client, registry=_REGISTRY, model=_MODEL)
    assert len(comments) == 1
    assert comments[0].path == "app/foo.py"
    assert comments[0].severity == "suggestion"


def test_run_review_empty_findings():
    client = _mock_client(json.dumps([_VALID_COMMENT]))
    comments = run_review(_DIFF, _CONTEXT, [], client=client, registry=_REGISTRY, model=_MODEL)
    # findings_text should be "None" — prompt formats without error
    assert len(comments) == 1


def test_run_review_invalid_json_raises():
    client = _mock_client("not json at all")
    with pytest.raises(ReviewError):
        run_review(_DIFF, _CONTEXT, _FINDINGS, client=client, registry=_REGISTRY, model=_MODEL)


def test_run_review_schema_mismatch_raises():
    client = _mock_client(json.dumps([{"wrong": "shape"}]))
    with pytest.raises(ReviewError):
        run_review(_DIFF, _CONTEXT, _FINDINGS, client=client, registry=_REGISTRY, model=_MODEL)
