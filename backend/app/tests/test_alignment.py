"""Tests for hourly WINDFOR and half-hour FUELHH alignment."""

import pandas as pd

from app.analytics.alignment import hourly_actuals


def test_hourly_actuals_averages_both_half_hour_periods():
    actuals = pd.DataFrame({
        "start_time": pd.to_datetime(
            ["2026-01-01T00:00:00Z", "2026-01-01T00:30:00Z"],
            utc=True,
        ),
        "generation_mw": [100.0, 120.0],
    })

    result = hourly_actuals(actuals)

    assert len(result) == 1
    assert result.iloc[0]["start_time"] == pd.Timestamp("2026-01-01T00:00:00Z")
    assert result.iloc[0]["generation_mw"] == 110.0


def test_hourly_actuals_drops_incomplete_hour():
    actuals = pd.DataFrame({
        "start_time": pd.to_datetime(["2026-01-01T00:00:00Z"], utc=True),
        "generation_mw": [100.0],
    })

    assert hourly_actuals(actuals).empty


def test_hourly_actuals_returns_empty_for_missing_columns():
    assert hourly_actuals(pd.DataFrame()).columns.tolist() == [
        "start_time",
        "generation_mw",
    ]
