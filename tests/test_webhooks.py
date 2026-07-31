import hashlib
import hmac
import json

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

SECRET = "test-secret"

PR_PAYLOAD = json.dumps({
    "action": "opened",
    "repository": {"full_name": "org/repo"},
    "pull_request": {"number": 1},
}).encode()


def _sign(body: bytes) -> str:
    mac = hmac.new(SECRET.encode(), body, hashlib.sha256)
    return f"sha256={mac.hexdigest()}"


def test_valid_signature_handled_event():
    response = client.post(
        "/webhooks/github",
        content=PR_PAYLOAD,
        headers={
            "X-Hub-Signature-256": _sign(PR_PAYLOAD),
            "X-GitHub-Event": "pull_request",
            "X-GitHub-Delivery": "abc-123",
        },
    )
    assert response.status_code == 200


def test_forged_signature():
    response = client.post(
        "/webhooks/github",
        content=PR_PAYLOAD,
        headers={
            "X-Hub-Signature-256": "sha256=deadbeef",
            "X-GitHub-Event": "pull_request",
        },
    )
    assert response.status_code == 401


def test_ignored_event():
    body = json.dumps({
        "action": "closed",
        "repository": {"full_name": "org/repo"},
        "pull_request": {"number": 1},
    }).encode()
    response = client.post(
        "/webhooks/github",
        content=body,
        headers={
            "X-Hub-Signature-256": _sign(body),
            "X-GitHub-Event": "pull_request",
        },
    )
    assert response.status_code == 204
