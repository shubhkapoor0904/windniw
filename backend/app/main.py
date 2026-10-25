"""Wind Forecast Decision Support — FastAPI Application.

A backend API for UK energy utility day-ahead wind generation
forecast analysis, supporting procurement decisions.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.data.cache import cache
from app.routes import health, actuals, forecast, compare, metrics, meta

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: check data cache on startup."""
    logger.info("=" * 60)
    logger.info("Starting Wind Forecast Decision Support API")
    logger.info("=" * 60)

    # Check cached data on startup
    if cache.has_data():
        meta_info = cache.get_metadata()
        logger.info(
            f"Cache loaded: {meta_info.get('actuals_count', 0)} actuals, "
            f"{meta_info.get('forecasts_count', 0)} forecasts"
        )
    else:
        logger.warning(
            "No cached data found! Run 'python -m app.data.fetch_data' to "
            "fetch data from Elexon BMRS."
        )

    yield

    logger.info("Shutting down Wind Forecast API")


app = FastAPI(
    title=settings.app_name,
    description=(
        "API for UK day-ahead wind generation forecast analysis. "
        "Supports procurement decision-making by providing forecast "
        "accuracy metrics, uncertainty bands, and horizon analysis."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
origins = [o.strip() for o in settings.cors_origins.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(meta.router, prefix="/api", tags=["Meta"])
app.include_router(actuals.router, prefix="/api", tags=["Actuals"])
app.include_router(forecast.router, prefix="/api", tags=["Forecast"])
app.include_router(compare.router, prefix="/api", tags=["Compare"])
app.include_router(metrics.router, prefix="/api", tags=["Metrics"])


@app.get("/")
async def root():
    """Root endpoint — redirect to docs."""
    return {
        "name": settings.app_name,
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/health",
    }
