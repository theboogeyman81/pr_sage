import os

from celery import Celery

_redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "pr_sage",
    broker=_redis_url,
    backend=_redis_url,
    include=["app.tasks.review"],
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)


def configure_celery(redis_url: str) -> None:
    celery_app.conf.broker_url = redis_url
    celery_app.conf.result_backend = redis_url
