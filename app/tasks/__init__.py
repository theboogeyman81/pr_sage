from celery import Celery

celery_app = Celery(
    "pr_sage",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0",
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
