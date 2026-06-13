from fastapi import FastAPI

from app.logging_config import configure_logging
from app.routes.health import router as health_router

configure_logging()

app = FastAPI()
app.include_router(health_router)
