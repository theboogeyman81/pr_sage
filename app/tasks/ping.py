import logging

from app.tasks import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="tasks.ping")
def ping() -> str:
    logger.info("ping task executed")
    return "pong"
