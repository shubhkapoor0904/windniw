"""Compare endpoint: forecast vs actual side-by-side."""

from fastapi import APIRouter, Query, HTTPException
from datetime import date, timedelta
import pandas as pd

from app.models import ComparisonRecord, ComparisonResponse
from app.data.cache import cache
from app.analytics.selection import compute_cutoff_time, select_latest_forecast
from app.analytics.alignment import hourly_actuals

router = APIRouter()


@router.get("/compare", response_model=ComparisonResponse)
async def get_comparison(
    start: str = Query(
        ...,
        description="Start date (YYYY-MM-DD) in January 2026",
    ),
    end: str = Query(
        ...,
        description="End date (YYYY-MM-DD) in January 2026",
    ),
    cutoffHour: int = Query(
        9,
        ge=0,
        le=23,
        description="Decision cutoff hour in Europe/London (D-1)",
    ),
    cutoffMinute: int = Query(0, ge=0, le=59),
) -> ComparisonResponse:
    """Compare latest forecast vs actuals for a date range.

    For each hourly forecast target in the range, shows the hourly mean
    actual generation, the forecast selected at the decision cutoff, and error.
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

    # Load actuals
    actuals_df = hourly_actuals(
        cache.get_actuals(start_date.isoformat(), end_date.isoformat())
    )

    # Load and select forecasts day by day
    all_selected = []
    current = start_date
    while current <= end_date:
        cutoff = compute_cutoff_time(current, cutoffHour, cutoffMinute)
        day_start = f"{current.isoformat()}T00:00:00Z"
        day_end = f"{current.isoformat()}T23:59:59Z"

        day_forecasts = cache.get_forecasts(
            target_start=day_start,
            target_end=day_end,
            publish_before=cutoff.strftime("%Y-%m-%dT%H:%M:%SZ"),
        )

        if not day_forecasts.empty:
            selected = select_latest_forecast(day_forecasts, cutoff)
            all_selected.append(selected)

        current += timedelta(days=1)

    # Merge
    if all_selected:
        forecasts_selected = pd.concat(all_selected, ignore_index=True)
    else:
        forecasts_selected = pd.DataFrame(
            columns=["start_time", "publish_time", "generation_mw", "horizon_hours"]
        )

    # Outer join on start_time
    if not actuals_df.empty and not forecasts_selected.empty:
        merged = pd.merge(
            actuals_df[["start_time", "generation_mw"]],
            forecasts_selected[["start_time", "publish_time", "generation_mw", "horizon_hours"]],
            on="start_time",
            how="outer",
            suffixes=("_actual", "_forecast"),
        )
    elif not actuals_df.empty:
        merged = actuals_df[["start_time", "generation_mw"]].copy()
        merged.rename(columns={"generation_mw": "generation_mw_actual"}, inplace=True)
        merged["generation_mw_forecast"] = None
        merged["publish_time"] = None
        merged["horizon_hours"] = None
    elif not forecasts_selected.empty:
        merged = forecasts_selected.copy()
        merged.rename(columns={"generation_mw": "generation_mw_forecast"}, inplace=True)
        merged["generation_mw_actual"] = None
    else:
        return ComparisonResponse(data=[], count=0)

    merged = merged.sort_values("start_time").reset_index(drop=True)

    # Compute error
    data = []
    for _, row in merged.iterrows():
        actual = row.get("generation_mw_actual")
        forecast = row.get("generation_mw_forecast")
        error = None
        abs_error = None

        if actual is not None and forecast is not None and pd.notna(actual) and pd.notna(forecast):
            error = round(forecast - actual, 2)
            abs_error = round(abs(error), 2)

        publish_time = row.get("publish_time")
        if publish_time is not None and pd.isna(publish_time):
            publish_time = None
        horizon = row.get("horizon_hours")
        if horizon is not None and pd.isna(horizon):
            horizon = None

        data.append(ComparisonRecord(
            start_time=row["start_time"],
            actual_mw=round(actual, 1) if actual is not None and pd.notna(actual) else None,
            forecast_mw=round(forecast, 1) if forecast is not None and pd.notna(forecast) else None,
            publish_time=publish_time,
            horizon_hours=horizon,
            error_mw=error,
            abs_error_mw=abs_error,
        ))

    return ComparisonResponse(data=data, count=len(data))
