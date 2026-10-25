"""Tests for forecast selection logic."""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta, timezone

from app.analytics.selection import (
    compute_cutoff_time,
    select_latest_forecast,
    compute_horizon,
)


class TestComputeCutoffTime:
    """Tests for decision cutoff time calculation."""

    def test_basic_cutoff_jan_2(self):
        """D=Jan 2 → cutoff = Jan 1 at 09:00 London = 09:00 UTC (no DST in Jan)."""
        cutoff = compute_cutoff_time(date(2026, 1, 2), cutoff_hour=9)
        assert cutoff.hour == 9
        assert cutoff.day == 1
        assert cutoff.month == 1
        assert cutoff.tzinfo is not None

    def test_cutoff_different_hour(self):
        """Custom cutoff hour works."""
        cutoff = compute_cutoff_time(date(2026, 1, 5), cutoff_hour=14)
        assert cutoff.hour == 14
        assert cutoff.day == 4  # D-1

    def test_cutoff_jan_1(self):
        """D=Jan 1 → cutoff = Dec 31 at 09:00."""
        cutoff = compute_cutoff_time(date(2026, 1, 1), cutoff_hour=9)
        assert cutoff.day == 31
        assert cutoff.month == 12
        assert cutoff.year == 2025

    def test_cutoff_is_utc_aware(self):
        """Cutoff must be timezone-aware (UTC)."""
        cutoff = compute_cutoff_time(date(2026, 1, 15))
        assert cutoff.tzinfo is not None


class TestSelectLatestForecast:
    """Tests for the core selection logic: latest publishTime <= cutoff."""

    def _make_df(self, rows):
        """Helper to create a forecast DataFrame."""
        df = pd.DataFrame(rows, columns=["start_time", "publish_time", "generation_mw"])
        df["start_time"] = pd.to_datetime(df["start_time"], utc=True)
        df["publish_time"] = pd.to_datetime(df["publish_time"], utc=True)
        return df

    def test_picks_latest_before_cutoff(self):
        """Should pick forecast with max publishTime <= cutoff."""
        cutoff = datetime(2026, 1, 1, 9, 0, 0, tzinfo=timezone.utc)
        df = self._make_df([
            ("2026-01-02T12:00:00Z", "2025-12-31T06:00:00Z", 5000),  # early
            ("2026-01-02T12:00:00Z", "2026-01-01T08:00:00Z", 5500),  # latest before cutoff
            ("2026-01-02T12:00:00Z", "2026-01-01T10:00:00Z", 6000),  # AFTER cutoff
        ])

        result = select_latest_forecast(df, cutoff)
        assert len(result) == 1
        assert result.iloc[0]["generation_mw"] == 5500

    def test_excludes_after_cutoff(self):
        """Forecasts published after cutoff must be excluded."""
        cutoff = datetime(2026, 1, 1, 9, 0, 0, tzinfo=timezone.utc)
        df = self._make_df([
            ("2026-01-02T12:00:00Z", "2026-01-01T12:00:00Z", 7000),
        ])

        result = select_latest_forecast(df, cutoff)
        assert result.empty

    def test_multiple_targets(self):
        """Each target time gets its own latest forecast."""
        cutoff = datetime(2026, 1, 1, 9, 0, 0, tzinfo=timezone.utc)
        df = self._make_df([
            ("2026-01-02T00:00:00Z", "2026-01-01T08:00:00Z", 4000),
            ("2026-01-02T00:00:00Z", "2026-01-01T06:00:00Z", 3500),
            ("2026-01-02T00:30:00Z", "2026-01-01T07:00:00Z", 4100),
            ("2026-01-02T00:30:00Z", "2026-01-01T08:30:00Z", 4200),
        ])

        result = select_latest_forecast(df, cutoff)
        assert len(result) == 2
        # First target: latest is 08:00
        t1 = result[result["start_time"] == pd.Timestamp("2026-01-02T00:00:00Z")]
        assert t1.iloc[0]["generation_mw"] == 4000
        # Second target: latest is 08:30
        t2 = result[result["start_time"] == pd.Timestamp("2026-01-02T00:30:00Z")]
        assert t2.iloc[0]["generation_mw"] == 4200

    def test_empty_dataframe(self):
        """Empty input returns empty output."""
        cutoff = datetime(2026, 1, 1, 9, 0, 0, tzinfo=timezone.utc)
        df = pd.DataFrame(columns=["start_time", "publish_time", "generation_mw"])
        result = select_latest_forecast(df, cutoff)
        assert result.empty

    def test_horizon_is_calculated(self):
        """Result should include horizon_hours."""
        cutoff = datetime(2026, 1, 1, 9, 0, 0, tzinfo=timezone.utc)
        df = self._make_df([
            ("2026-01-02T12:00:00Z", "2026-01-01T08:00:00Z", 5000),
        ])

        result = select_latest_forecast(df, cutoff)
        assert "horizon_hours" in result.columns
        # Horizon = 12:00 Jan 2 - 08:00 Jan 1 = 28 hours
        assert result.iloc[0]["horizon_hours"] == 28.0

    def test_exact_cutoff_included(self):
        """Forecast published exactly at cutoff should be included."""
        cutoff = datetime(2026, 1, 1, 9, 0, 0, tzinfo=timezone.utc)
        df = self._make_df([
            ("2026-01-02T12:00:00Z", "2026-01-01T09:00:00Z", 5000),
        ])

        result = select_latest_forecast(df, cutoff)
        assert len(result) == 1


class TestComputeHorizon:
    """Tests for horizon calculation."""

    def test_basic_horizon(self):
        """Simple horizon calculation."""
        start = datetime(2026, 1, 2, 12, 0, 0, tzinfo=timezone.utc)
        publish = datetime(2026, 1, 1, 8, 0, 0, tzinfo=timezone.utc)
        assert compute_horizon(start, publish) == 28.0

    def test_zero_horizon(self):
        """Same time = zero horizon."""
        t = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        assert compute_horizon(t, t) == 0.0

    def test_half_hour_precision(self):
        """Horizon with 30-min granularity."""
        start = datetime(2026, 1, 1, 12, 30, 0, tzinfo=timezone.utc)
        publish = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        assert compute_horizon(start, publish) == 0.5
