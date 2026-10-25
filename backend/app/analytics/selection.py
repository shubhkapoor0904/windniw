"""Forecast selection logic.

Core business logic: given a target delivery time T and a decision cutoff,
select the forecast with the maximum publishTime <= cutoff.

This is the "latest forecast at decision time" — the most current forecast
available to the buyer when they make their procurement decision.
"""

import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta, timezone
from typing import Optional, Tuple
import pytz

LONDON_TZ = pytz.timezone("Europe/London")


def compute_cutoff_time(
    target_date: date,
    cutoff_hour: int = 9,
) -> datetime:
    """Compute the decision cutoff datetime for a given delivery date.

    The decision for delivery day D is made on D-1 at cutoff_hour
    in Europe/London timezone. This function returns the cutoff
    as a UTC-aware datetime.

    Args:
        target_date: The delivery date (D)
        cutoff_hour: Hour of day in Europe/London for the cutoff (default 9)

    Returns:
        UTC-aware datetime representing the cutoff
    """
    # D-1 at cutoff_hour in London time
    d_minus_1 = target_date - timedelta(days=1)
    london_cutoff = LONDON_TZ.localize(
        datetime(d_minus_1.year, d_minus_1.month, d_minus_1.day, cutoff_hour, 0, 0)
    )
    return london_cutoff.astimezone(timezone.utc)


def select_latest_forecast(
    forecasts_df: pd.DataFrame,
    cutoff: datetime,
) -> pd.DataFrame:
    """Select the latest available forecast for each target time.

    For each unique start_time (target delivery half-hour), pick the
    forecast row with the maximum publishTime that is still <= cutoff.

    This represents what the buyer would actually see at decision time.

    Args:
        forecasts_df: DataFrame with columns [start_time, publish_time, generation_mw]
                      Both time columns must be UTC-aware.
        cutoff: Decision cutoff datetime (UTC-aware)

    Returns:
        DataFrame with one row per start_time, containing the latest forecast
        available at the cutoff. Adds 'horizon_hours' column.
    """
    if forecasts_df.empty:
        return pd.DataFrame(
            columns=["start_time", "publish_time", "generation_mw", "horizon_hours"]
        )

    # Ensure datetime types
    df = forecasts_df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df["start_time"]):
        df["start_time"] = pd.to_datetime(df["start_time"], utc=True)
    if not pd.api.types.is_datetime64_any_dtype(df["publish_time"]):
        df["publish_time"] = pd.to_datetime(df["publish_time"], utc=True)

    # Ensure cutoff is UTC-aware
    if cutoff.tzinfo is None:
        cutoff = cutoff.replace(tzinfo=timezone.utc)

    # Filter: only forecasts published before or at the cutoff
    mask = df["publish_time"] <= cutoff
    available = df[mask].copy()

    if available.empty:
        return pd.DataFrame(
            columns=["start_time", "publish_time", "generation_mw", "horizon_hours"]
        )

    # For each target time, pick the forecast with latest publish time
    idx = available.groupby("start_time")["publish_time"].idxmax()
    selected = available.loc[idx].copy()

    # Calculate horizon: how many hours before the target the forecast was made
    selected["horizon_hours"] = (
        (selected["start_time"] - selected["publish_time"]).dt.total_seconds() / 3600.0
    ).round(2)

    return selected.sort_values("start_time").reset_index(drop=True)


def compute_horizon(
    start_time: datetime,
    publish_time: datetime,
) -> float:
    """Calculate forecast horizon in hours.

    Args:
        start_time: Target delivery time
        publish_time: When the forecast was published

    Returns:
        Horizon in hours (start_time - publish_time)
    """
    delta = start_time - publish_time
    return round(delta.total_seconds() / 3600.0, 2)
