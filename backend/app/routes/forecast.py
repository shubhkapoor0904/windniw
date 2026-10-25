"""Forecast endpoints: latest forecast at decision time."""

from fastapi import APIRouter, Query, HTTPException
from datetime import date, datetime, timezone
from typing import Optional
import pandas as pd

from app.models import (
    LatestForecastRecord,
    LatestForecastResponse,
    ForecastSummary,
)
from app.data.cache import cache
from app.analytics.selection import compute_cutoff_time, select_latest_forecast
from app.analytics.horizon import compute_uncertainty_bands
from app.analytics.metrics import compute_error

router = APIRouter()


@router.get("/forecast/latest", response_model=LatestForecastResponse)
async def get_latest_forecast(
    targetDate: str = Query(
        ...,
        description="Delivery date (YYYY-MM-DD) in January 2026",
    ),
    cutoffHour: int = Query(
        9,
        ge=0,
        le=23,
        description="Decision cutoff hour in Europe/London time (D-1). Default 09:00.",
    ),
) -> LatestForecastResponse:
    """Get the latest wind forecast available at decision time.

    For each half-hour slot on the target delivery day, returns the most
    recently published forecast that was available at the decision cutoff
    (D-1 at cutoffHour in Europe/London time).

    Includes uncertainty bands derived from historical error percentiles.
    """
    # Validate target date
    try:
        target = date.fromisoformat(targetDate)
    except ValueError:
        raise HTTPException(400, "Invalid date format. Use YYYY-MM-DD.")

    if target < date(2026, 1, 1) or target > date(2026, 1, 31):
        raise HTTPException(400, "Target date must be in January 2026.")

    # Compute cutoff
    cutoff = compute_cutoff_time(target, cutoff_hour=cutoffHour)

    # Load forecasts for the target date
    target_start = f"{target.isoformat()}T00:00:00+00:00"
    target_end = f"{target.isoformat()}T23:59:59+00:00"

    forecasts_df = cache.get_forecasts(
        target_start=target_start,
        target_end=target_end,
        publish_before=cutoff.isoformat(),
    )

    if forecasts_df.empty:
        return LatestForecastResponse(
            target_date=target,
            cutoff_time=cutoff,
            data=[],
            summary=None,
        )

    # Select latest forecast for each half-hour
    selected = select_latest_forecast(forecasts_df, cutoff)

    # Compute uncertainty bands from historical errors
    # Load all comparison data for the month to build error history
    actuals_df = cache.get_actuals("2026-01-01", "2026-01-31")
    all_forecasts_df = cache.get_forecasts(
        target_start="2026-01-01T00:00:00+00:00",
        target_end="2026-01-31T23:59:59+00:00",
    )

    # Build historical error data per horizon
    error_data = _build_error_history(actuals_df, all_forecasts_df, cutoffHour)

    # Build response
    data = []
    for _, row in selected.iterrows():
        horizon = row["horizon_hours"]

        # Get uncertainty bands for this horizon
        if not error_data.empty:
            p10_err, p90_err = compute_uncertainty_bands(error_data, horizon)
            # Band: actual likely between forecast - p90_error and forecast - p10_error
            unc_low = max(0, row["generation_mw"] - p90_err)
            unc_high = max(0, row["generation_mw"] - p10_err)
        else:
            unc_low = None
            unc_high = None

        data.append(LatestForecastRecord(
            start_time=row["start_time"],
            publish_time=row["publish_time"],
            generation_mw=round(row["generation_mw"], 1),
            horizon_hours=horizon,
            uncertainty_low=round(unc_low, 1) if unc_low is not None else None,
            uncertainty_high=round(unc_high, 1) if unc_high is not None else None,
        ))

    # Summary
    if data:
        gens = [d.generation_mw for d in data]
        summary = ForecastSummary(
            peak_mw=max(gens),
            min_mw=min(gens),
            avg_mw=round(sum(gens) / len(gens), 1),
            total_mwh=round(sum(gens) * 0.5, 1),  # Each point is 30 min
            avg_horizon_hours=round(
                sum(d.horizon_hours for d in data) / len(data), 1
            ),
        )
    else:
        summary = None

    return LatestForecastResponse(
        target_date=target,
        cutoff_time=cutoff,
        data=data,
        summary=summary,
    )


def _build_error_history(
    actuals_df: pd.DataFrame,
    forecasts_df: pd.DataFrame,
    cutoff_hour: int,
) -> pd.DataFrame:
    """Build a DataFrame of errors with horizons for uncertainty band calculation.

    For each day in the data, selects the latest forecast at the cutoff,
    joins with actuals, and computes error and horizon.
    """
    if actuals_df.empty or forecasts_df.empty:
        return pd.DataFrame(columns=["horizon_hours", "error_mw"])

    # Get unique settlement dates from actuals
    if "settlement_date" in actuals_df.columns:
        dates = sorted(actuals_df["settlement_date"].unique())
    else:
        return pd.DataFrame(columns=["horizon_hours", "error_mw"])

    all_errors = []

    for d_str in dates:
        try:
            d = date.fromisoformat(str(d_str))
        except (ValueError, TypeError):
            continue

        cutoff = compute_cutoff_time(d, cutoff_hour)

        # Get forecasts for this day
        day_start = f"{d.isoformat()}T00:00:00+00:00"
        day_end = f"{d.isoformat()}T23:59:59+00:00"

        day_forecasts = forecasts_df[
            (forecasts_df["start_time"] >= pd.Timestamp(day_start, tz="UTC"))
            & (forecasts_df["start_time"] <= pd.Timestamp(day_end, tz="UTC"))
        ]

        if day_forecasts.empty:
            continue

        selected = select_latest_forecast(day_forecasts, cutoff)
        if selected.empty:
            continue

        # Join with actuals
        day_actuals = actuals_df[actuals_df["settlement_date"] == d_str]
        if day_actuals.empty:
            continue

        merged = pd.merge(
            selected,
            day_actuals[["start_time", "generation_mw"]],
            on="start_time",
            suffixes=("_forecast", "_actual"),
        )

        if merged.empty:
            continue

        merged["error_mw"] = merged["generation_mw_forecast"] - merged["generation_mw_actual"]
        all_errors.append(merged[["horizon_hours", "error_mw"]])

    if all_errors:
        return pd.concat(all_errors, ignore_index=True)
    return pd.DataFrame(columns=["horizon_hours", "error_mw"])
