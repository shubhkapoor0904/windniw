"""Align half-hourly FUELHH actuals to hourly WINDFOR target periods."""

import pandas as pd

FORECAST_INTERVAL_HOURS = 1.0
ACTUALS_PER_FORECAST = 2


def hourly_actuals(actuals: pd.DataFrame) -> pd.DataFrame:
    """Return complete hourly means from the two half-hourly actual periods.

    WINDFOR observations are hourly in the live January 2026 feed, while FUELHH
    outturn is half-hourly. Only hours with both actual intervals are retained;
    no forecast values are interpolated or duplicated.
    """
    columns = ["start_time", "generation_mw"]
    if actuals.empty or not {"start_time", "generation_mw"}.issubset(actuals.columns):
        return pd.DataFrame(columns=columns)

    frame = actuals[columns].copy()
    frame["start_time"] = pd.to_datetime(frame["start_time"], utc=True).dt.floor("h")
    grouped = frame.groupby("start_time", as_index=False).agg(
        generation_mw=("generation_mw", "mean"),
        actual_intervals=("generation_mw", "count"),
    )
    return grouped.loc[
        grouped["actual_intervals"] == ACTUALS_PER_FORECAST, columns
    ].reset_index(drop=True)
