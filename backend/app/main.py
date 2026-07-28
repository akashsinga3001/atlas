# backend/app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from datetime import datetime

from app.core.config import settings
from app.utils.logger import get_logger
from app.strategies.bootstrap import register_strategies
from app.exit_evaluators.bootstrap import register_exit_evaluators

from app.core.exceptions import AtlasException, atlas_exception_handler
from app.api.v1 import jobs, trades, signals, portfolio, quotes, fund, market

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_NAME} at {datetime.now()}")

    logger.info("Registering Strategies")
    register_strategies()
    logger.info("Strategies registered successfully")

    logger.info("Registering Exit Evaluators")
    register_exit_evaluators()
    logger.info("Exit Evaluators registered successfully")

    yield

    logger.info(f"Shutting down {settings.APP_NAME} at {datetime.now()}")


app = FastAPI(title=settings.APP_NAME, version="1.0.0", lifespan=lifespan)

# Middlewares
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# Exception Handler
app.add_exception_handler(AtlasException, atlas_exception_handler)

# Routers
app.include_router(jobs.router, prefix=f"{settings.API_V1_STR}/jobs", tags=["Jobs"])
app.include_router(trades.router, prefix=f"{settings.API_V1_STR}/trades", tags=["Trades"])
app.include_router(signals.router, prefix=f"{settings.API_V1_STR}/signals", tags=["Signals"])
app.include_router(portfolio.router, prefix=f"{settings.API_V1_STR}/portfolio", tags=["Portfolio"])
app.include_router(quotes.router, prefix=f"{settings.API_V1_STR}/quotes", tags=["Quotes"])
app.include_router(fund.router, prefix=f"{settings.API_V1_STR}/fund", tags=["Fund"])
app.include_router(market.router, prefix=f"{settings.API_V1_STR}/market", tags=["Market"])


@app.get("/", tags=["Root"])
async def read_root():
    return { "message": f"Welcome to {settings.APP_NAME}!"}


@app.get("/health", tags=["Health"])
async def health_check():
    return { "status": "healthy"}
