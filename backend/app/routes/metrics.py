"""Metrics endpoints: aggregated accuracy metrics and horizon analysis."""

from fastapi import APIRouter, Query, HTTPException
from datetime import date
from typing import Optional
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
) -> MetricsResponse:
    """Compute aggregated accuracy metrics for a date range.

    Compares the latest forecast (at the decision cutoff) against actuals
    for each half-hour in the date range.
    """
    try:
        start_date = date.fromisoformat(start)
        end_date = date.fromisoformat(end)
    except ValueError:
        raise HTTPException(400, "Invalid date format. Use YYYY-MM-DD.")

    if start_date < date(2026, 1, 1) or end_date > date(2026, 1, 31):
        raise HTTPException(400, "Dates must be within January 2026.")

    # Build comparison data
    actuals_df = cache.get_actuals(start_date.isoformat(), end_date.isoformat())
    forecast_mw, actual_mw, errors = _build_comparison_series(
        actuals_df, start_date, end_date, cutoffHour
    )

    if forecast_mw.empty or actual_mw.empty:
        return MetricsResponse(
            start_date=start_date,
            end_date=end_date,
            cutoff_hour=cutoffHour,
            metrics=AccuracyMetrics(
                mae=0, rmse=0, mape=None, bias=0,
                p50_abs_error=0, p90_abs_error=0, p99_abs_error=0,
                nmae=None, count=0,
            ),
            error_distribution=[],
        )

    metrics_dict = compute_all_metrics(forecast_mw, actual_mw)
    error_dist = compute_error_distribution(errors, n_bins=30)

    return MetricsResponse(
        start_date=start_date,
        end_date=end_date,
        cutoff_hour=cutoffHour,
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

    if start_date < date(2026, 1, 1) or end_date > date(2026, 1, 31):
        raise HTTPException(400, "Dates must be within January 2026.")

    # Build comparison data with horizons
    error_df = _build_error_with_horizon(start_date, end_date, cutoffHour)

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
) -> tuple:
    """Build aligned forecast and actual series for metric computation."""
    all_merged = []
    current = start_date

    while current <= end_date:
        cutoff = compute_cutoff_time(current, cutoff_hour)
        day_start = f"{current.isoformat()}T00:00:00+00:00"
        day_end = f"{current.isoformat()}T23:59:59+00:00"

        day_forecasts = cache.get_forecasts(
            target_start=day_start,
            target_end=day_end,
            publish_before=cutoff.isoformat(),
        )
        day_actuals = actuals_df[
            actuals_df["settlement_date"] == current.isoformat()
        ] if not actuals_df.empty and "settlement_date" in actuals_df.columns else pd.DataFrame()

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
        if current.day < 31:
            current = current.replace(day=current.day + 1)
        else:
            break

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
) -> pd.DataFrame:
    """Build a DataFrame with error and horizon for each half-hour."""
    actuals_df = cache.get_actuals(start_date.isoformat(), end_date.isoformat())
    all_data = []
    current = start_date

    while current <= end_date:
        cutoff = compute_cutoff_time(current, cutoff_hour)
        day_start = f"{current.isoformat()}T00:00:00+00:00"
        day_end = f"{current.isoformat()}T23:59:59+00:00"

        day_forecasts = cache.get_forecasts(
            target_start=day_start,
            target_end=day_end,
            publish_before=cutoff.isoformat(),
        )
        day_actuals = actuals_df[
            actuals_df["settlement_date"] == current.isoformat()
        ] if not actuals_df.empty and "settlement_date" in actuals_df.columns else pd.DataFrame()

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

        if current.day < 31:
            current = current.replace(day=current.day + 1)
        else:
            break

    if all_data:
        return pd.concat(all_data, ignore_index=True)
    return pd.DataFrame(columns=["horizon_hours", "error_mw"])
