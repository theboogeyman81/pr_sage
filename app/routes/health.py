import structlog
from fastapi import APIRouter

router = APIRouter()
logger = structlog.get_logger()


@router.get("/health")
def health() -> dict[str, str]:
    logger.info("health check")
    return {"status": "ok"}
