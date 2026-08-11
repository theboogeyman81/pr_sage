import hashlib
import hmac
import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.tasks import celery_app

client = TestClient(app)

_FAKE_DIFF = "diff --git a/foo.py b/foo.py\n--- a/foo.py\n+++ b/foo.py\n@@ -1 +1,2 @@\n+x = 1\n"


def _sign(body: bytes, secret: str) -> str:
    mac = hmac.new(secret.encode(), body, hashlib.sha256)
    return f"sha256={mac.hexdigest()}"


@pytest.fixture(autouse=True)
def _celery_eager():
    celery_app.conf.task_always_eager = True
    yield
    celery_app.conf.task_always_eager = False


def test_webhook_enqueues_review_pr():
    payload = {
        "action": "opened",
        "repository": {"full_name": "owner/repo"},
        "pull_request": {"number": 7},
        "installation": {"id": 42},
    }
    body = json.dumps(payload).encode()

    with patch("app.tasks.review._get_auth", return_value=MagicMock()), \
         patch("app.tasks.review.fetch_pr_diff", return_value=_FAKE_DIFF) as mock_fetch:
        response = client.post(
            "/webhooks/github",
            content=body,
            headers={
                "X-Hub-Signature-256": _sign(body, "test-secret"),
                "X-GitHub-Event": "pull_request",
                "X-GitHub-Delivery": "abc-123",
            },
        )

    assert response.status_code == 200
    mock_fetch.assert_called_once_with(
        "owner/repo", 7, 42, auth=mock_fetch.call_args.kwargs["auth"]
    )
