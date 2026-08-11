from unittest.mock import MagicMock, patch

import structlog
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.logging_config import configure_logging
from app.middleware.correlation import CorrelationMiddleware


def test_configure_logging_runs():
    configure_logging()  # must not raise


def test_middleware_injects_request_id():
    _app = FastAPI()
    _app.add_middleware(CorrelationMiddleware)

    @_app.get("/probe")
    async def probe(request: Request):
        return JSONResponse({"request_id": request.state.request_id})

    client = TestClient(_app)
    resp = client.get("/probe")
    assert resp.status_code == 200
    rid = resp.json()["request_id"]
    assert isinstance(rid, str) and len(rid) == 36  # UUID format


def test_review_pr_accepts_correlation_id():
    from app.tasks.review import review_pr

    with (
        patch("app.tasks.review._get_auth", return_value=MagicMock()),
        patch("app.tasks.review.fetch_pr_diff", return_value="diff --git a/f.py\n+x=1\n"),
    ):
        review_pr("owner/repo", 1, 99, correlation_id="test-corr-id")
