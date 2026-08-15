import hashlib
import hmac
import json

import structlog
from fastapi import APIRouter, Request, Response

from app.config import get_settings
from app.tasks.review import review_pr

logger = structlog.get_logger()
router = APIRouter()

_HANDLED_ACTIONS = {"opened", "synchronize", "reopened"}


def _verify_signature(secret: str, body: bytes, header: str | None) -> bool:
    if not header or not header.startswith("sha256="):
        return False
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header.removeprefix("sha256="))


@router.post("/webhooks/github")
async def github_webhook(request: Request) -> Response:
    body = await request.body()
    sig_header = request.headers.get("X-Hub-Signature-256")

    if not _verify_signature(get_settings().GITHUB_WEBHOOK_SECRET, body, sig_header):
        return Response(status_code=401)

    event = request.headers.get("X-GitHub-Event", "")
    payload = json.loads(body)
    action = payload.get("action", "")

    if event != "pull_request" or action not in _HANDLED_ACTIONS:
        return Response(status_code=204)

    delivery_id = request.headers.get("X-GitHub-Delivery", "unknown")
    repo = payload.get("repository", {}).get("full_name", "unknown")
    pr_number = payload.get("pull_request", {}).get("number", "unknown")
    installation_id = payload.get("installation", {}).get("id", 0)
    head_sha = payload.get("pull_request", {}).get("head", {}).get("sha", "")
    logger.info("pr_event", delivery=delivery_id, repo=repo, pr=pr_number, action=action)
    review_pr.delay(
        repo, pr_number, installation_id, head_sha,
        correlation_id=getattr(request.state, "request_id", None),
    )

    return Response(status_code=200)
