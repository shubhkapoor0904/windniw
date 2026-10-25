"""Meta endpoint: data coverage and cache info."""

from fastapi import APIRouter
from app.models import MetaResponse
from app.data.cache import cache

router = APIRouter()


@router.get("/meta", response_model=MetaResponse)
async def get_meta() -> MetaResponse:
    """Return metadata about cached data coverage."""
    meta = cache.get_metadata()
    return MetaResponse(
        actuals_count=meta.get("actuals_count", 0),
        forecasts_count=meta.get("forecasts_count", 0),
        actuals_date_range=meta.get("actuals_date_range"),
        forecasts_publish_range=meta.get("forecasts_publish_range"),
        forecasts_target_range=meta.get("forecasts_target_range"),
        last_fetched=meta.get("FUELHH_WIND_last_fetched") or meta.get("WINDFOR_last_fetched"),
        cache_size_mb=meta.get("cache_size_mb"),
    )
