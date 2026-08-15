import structlog

from app.tasks import celery_app

logger = structlog.get_logger()


@celery_app.task(name="tasks.ping")
def ping() -> str:
    logger.info("ping task executed")
    return "pong"
