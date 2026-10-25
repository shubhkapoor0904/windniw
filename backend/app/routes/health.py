"""Health check endpoint."""

from fastapi import APIRouter
from app.models import HealthResponse
from app.data.cache import cache

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint. Reports data availability."""
    meta = cache.get_metadata()
    return HealthResponse(
        status="ok",
        data_loaded=cache.has_data(),
        actuals_count=meta.get("actuals_count", 0),
        forecasts_count=meta.get("forecasts_count", 0),
    )
