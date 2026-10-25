"""Metrics endpoints: aggregated accuracy metrics and horizon analysis."""

from fastapi import APIRouter, Query, HTTPException
from datetime import date, timedelta
import pandas as pd

from app.models import (
    AccuracyMetrics,
    MetricsResponse,
    ErrorBucket,
    HorizonBucket,
    HorizonResponse,
)
from app.data.cache import cache
from app.analytics.selection import compute_cutoff_time, select_latest_forecast
from app.analytics.metrics import compute_all_metrics, compute_error, compute_error_distribution
from app.analytics.horizon import compute_horizon_metrics
from app.analytics.alignment import hourly_actuals

router = APIRouter()


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(
    start: str = Query(
        "2026-01-01",
        description="Start date (YYYY-MM-DD) in January 2026",
    ),
    end: str = Query(
        "2026-01-31",
        description="End date (YYYY-MM-DD) in January 2026",
    ),
    cutoffHour: int = Query(
        9,
        ge=0,
        le=23,
        description="Decision cutoff hour in Europe/London (D-1)",
    ),
    cutoffMinute: int = Query(0, ge=0, le=59),
) -> MetricsResponse:
    """Compute aggregated accuracy metrics for a date range.

    Compares the latest hourly forecast against the corresponding hourly mean
    of two half-hour FUELHH actuals.
    """
    try:
        start_date = date.fromisoformat(start)
        end_date = date.fromisoformat(end)
    except ValueError:
        raise HTTPException(400, "Invalid date format. Use YYYY-MM-DD.")

    if (
        start_date < date(2026, 1, 1)
        or start_date > date(2026, 1, 31)
        or end_date < date(2026, 1, 1)
        or end_date > date(2026, 1, 31)
    ):
        raise HTTPException(400, "Dates must be within January 2026.")
    if start_date > end_date:
        raise HTTPException(400, "start must be before or equal to end.")

    # Build comparison data
    actuals_df = hourly_actuals(
        cache.get_actuals(start_date.isoformat(), end_date.isoformat())
    )
    forecast_mw, actual_mw, errors = _build_comparison_series(
        actuals_df, start_date, end_date, cutoffHour, cutoffMinute
    )

    metrics_dict = compute_all_metrics(forecast_mw, actual_mw)
    error_dist = compute_error_distribution(errors, n_bins=30)

    return MetricsResponse(
        start_date=start_date,
        end_date=end_date,
        cutoff_hour=cutoffHour,
        cutoff_minute=cutoffMinute,
        metrics=AccuracyMetrics(**metrics_dict),
        error_distribution=[ErrorBucket(**b) for b in error_dist],
    )


@router.get("/metrics/by-horizon", response_model=HorizonResponse)
async def get_metrics_by_horizon(
    start: str = Query(
        "2026-01-01",
        description="Start date (YYYY-MM-DD) in January 2026",
    ),
    end: str = Query(
        "2026-01-31",
        description="End date (YYYY-MM-DD) in January 2026",
    ),
    cutoffHour: int = Query(
        9,
        ge=0,
        le=23,
        description="Decision cutoff hour in Europe/London (D-1)",
    ),
    cutoffMinute: int = Query(0, ge=0, le=59),
) -> HorizonResponse:
    """Compute error metrics grouped by forecast horizon.

    Shows how MAE, RMSE, bias change as the forecast gets staler.
    Helps buyers understand: "How much should I trust a forecast
    made X hours ahead?"
    """
    try:
        start_date = date.fromisoformat(start)
        end_date = date.fromisoformat(end)
    except ValueError:
        raise HTTPException(400, "Invalid date format. Use YYYY-MM-DD.")

    if (
        start_date < date(2026, 1, 1)
        or start_date > date(2026, 1, 31)
        or end_date < date(2026, 1, 1)
        or end_date > date(2026, 1, 31)
    ):
        raise HTTPException(400, "Dates must be within January 2026.")
    if start_date > end_date:
        raise HTTPException(400, "start must be before or equal to end.")

    # Build comparison data with horizons
    error_df = _build_error_with_horizon(
        start_date, end_date, cutoffHour, cutoffMinute
    )

    if error_df.empty:
        return HorizonResponse(buckets=[])

    horizon_metrics = compute_horizon_metrics(error_df)
    return HorizonResponse(
        buckets=[HorizonBucket(**b) for b in horizon_metrics],
    )


def _build_comparison_series(
    actuals_df: pd.DataFrame,
    start_date: date,
    end_date: date,
    cutoff_hour: int,
    cutoff_minute: int = 0,
) -> tuple:
    """Build aligned forecast and actual series for metric computation."""
    all_merged = []
    current = start_date

    while current <= end_date:
        cutoff = compute_cutoff_time(current, cutoff_hour, cutoff_minute)
        day_start = f"{current.isoformat()}T00:00:00Z"
        day_end = f"{current.isoformat()}T23:59:59Z"

        day_forecasts = cache.get_forecasts(
            target_start=day_start,
            target_end=day_end,
            publish_before=cutoff.strftime("%Y-%m-%dT%H:%M:%SZ"),
        )
        day_actuals = actuals_df[
            actuals_df["start_time"].dt.strftime("%Y-%m-%d") == current.isoformat()
        ] if not actuals_df.empty else pd.DataFrame()

        if not day_forecasts.empty and not day_actuals.empty:
            selected = select_latest_forecast(day_forecasts, cutoff)
            merged = pd.merge(
                selected[["start_time", "generation_mw"]],
                day_actuals[["start_time", "generation_mw"]],
                on="start_time",
                suffixes=("_forecast", "_actual"),
            )
            all_merged.append(merged)

        # Advance to next day
        current += timedelta(days=1)

    if not all_merged:
        return pd.Series(dtype=float), pd.Series(dtype=float), pd.Series(dtype=float)

    combined = pd.concat(all_merged, ignore_index=True)
    forecast_mw = combined["generation_mw_forecast"]
    actual_mw = combined["generation_mw_actual"]
    errors = compute_error(forecast_mw, actual_mw)

    return forecast_mw, actual_mw, errors


def _build_error_with_horizon(
    start_date: date,
    end_date: date,
    cutoff_hour: int,
    cutoff_minute: int = 0,
) -> pd.DataFrame:
    """Build a DataFrame with error and horizon for each hourly target."""
    actuals_df = hourly_actuals(
        cache.get_actuals(start_date.isoformat(), end_date.isoformat())
    )
    all_data = []
    current = start_date

    while current <= end_date:
        cutoff = compute_cutoff_time(current, cutoff_hour, cutoff_minute)
        day_start = f"{current.isoformat()}T00:00:00Z"
        day_end = f"{current.isoformat()}T23:59:59Z"

        day_forecasts = cache.get_forecasts(
            target_start=day_start,
            target_end=day_end,
            publish_before=cutoff.strftime("%Y-%m-%dT%H:%M:%SZ"),
        )
        day_actuals = actuals_df[
            actuals_df["start_time"].dt.strftime("%Y-%m-%d") == current.isoformat()
        ] if not actuals_df.empty else pd.DataFrame()

        if not day_forecasts.empty and not day_actuals.empty:
            selected = select_latest_forecast(day_forecasts, cutoff)
            merged = pd.merge(
                selected[["start_time", "generation_mw", "horizon_hours"]],
                day_actuals[["start_time", "generation_mw"]],
                on="start_time",
                suffixes=("_forecast", "_actual"),
            )
            if not merged.empty:
                merged["error_mw"] = (
                    merged["generation_mw_forecast"] - merged["generation_mw_actual"]
                )
                all_data.append(merged[["horizon_hours", "error_mw"]])

        current += timedelta(days=1)

    if all_data:
        return pd.concat(all_data, ignore_index=True)
    return pd.DataFrame(columns=["horizon_hours", "error_mw"])
