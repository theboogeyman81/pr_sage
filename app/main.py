from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings
from app.logging_config import configure_logging
from app.middleware.correlation import CorrelationMiddleware
from app.routes.health import router as health_router
from app.routes.metrics import router as metrics_router
from app.routes.webhooks import router as webhooks_router
from app.tasks import configure_celery

configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_celery(settings.REDIS_URL)
    yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(CorrelationMiddleware)
app.include_router(health_router)
app.include_router(metrics_router)
app.include_router(webhooks_router)
