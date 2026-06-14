# backend/app/main.py

from fastapi import FastAPI
from contextlib import asynccontextmanager
from datetime import datetime

from app.core.config import settings
from app.utils.logger import get_logger

from app.core.exceptions import AtlasException, atlas_exception_handler

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_NAME} at {datetime.now()}")

    yield

    logger.info(f"Shutting down {settings.APP_NAME} at {datetime.now()}")


app = FastAPI(title=settings.APP_NAME, version="1.0.0", lifespan=lifespan)

app.add_exception_handler(AtlasException, atlas_exception_handler)


@app.get("/", tags=["Root"])
async def read_root():
    return { "message": f"Welcome to {settings.APP_NAME}!"}


@app.get("/health", tags=["Health"])
async def health_check():
    return { "status": "healthy"}
