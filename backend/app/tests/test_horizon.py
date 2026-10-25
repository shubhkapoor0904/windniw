"""Tests for horizon analysis."""

import pandas as pd
import numpy as np

from app.analytics.horizon import (
    assign_horizon_bucket,
    compute_horizon_metrics,
    compute_uncertainty_bands,
)


class TestAssignHorizonBucket:
    def test_short_horizon(self):
        assert assign_horizon_bucket(3.0) == "0-6h"

    def test_medium_horizon(self):
        assert assign_horizon_bucket(15.0) == "12-24h"

    def test_long_horizon(self):
        assert assign_horizon_bucket(50.0) == "48-72h"

    def test_very_long_horizon(self):
        assert assign_horizon_bucket(100.0) == "72h+"

    def test_boundary_inclusive(self):
        """Lower bound is inclusive."""
        assert assign_horizon_bucket(6.0) == "6-12h"
        assert assign_horizon_bucket(0.0) == "0-6h"


class TestComputeHorizonMetrics:
    def _make_df(self, n=100):
        """Create a sample DataFrame with random errors at various horizons."""
        np.random.seed(42)
        horizons = np.random.uniform(0, 80, n)
        # Errors that grow with horizon (realistic pattern)
        errors = np.random.randn(n) * (1 + horizons / 10)
        return pd.DataFrame({
            "horizon_hours": horizons,
            "error_mw": errors,
        })

    def test_returns_correct_structure(self):
        df = self._make_df()
        results = compute_horizon_metrics(df)
        assert len(results) > 0
        for bucket in results:
            assert "horizon_label" in bucket
            assert "mae" in bucket
            assert "rmse" in bucket
            assert "bias" in bucket
            assert "p10_error" in bucket
            assert "p90_error" in bucket
            assert "count" in bucket

    def test_error_grows_with_horizon(self):
        """MAE should generally increase with horizon (by construction)."""
        df = self._make_df(1000)
        results = compute_horizon_metrics(df)
        if len(results) >= 2:
            # First bucket MAE should be less than last bucket MAE
            assert results[0]["mae"] < results[-1]["mae"]

    def test_empty_df(self):
        df = pd.DataFrame(columns=["horizon_hours", "error_mw"])
        assert compute_horizon_metrics(df) == []

    def test_missing_rows_are_ignored(self):
        df = pd.DataFrame({
            "horizon_hours": [1.0, np.nan],
            "error_mw": [5.0, 20.0],
        })
        results = compute_horizon_metrics(df)
        assert len(results) == 1
        assert results[0]["count"] == 1


class TestComputeUncertaintyBands:
    def test_basic_bands(self):
        np.random.seed(42)
        df = pd.DataFrame({
            "horizon_hours": [20] * 100,
            "error_mw": np.random.randn(100) * 100,
        })
        p10, p90 = compute_uncertainty_bands(df, forecast_horizon=20.0)
        # P10 should be negative (under-forecast), P90 positive (over-forecast)
        assert p10 < 0
        assert p90 > 0

    def test_empty_df(self):
        df = pd.DataFrame(columns=["horizon_hours", "error_mw"])
        assert compute_uncertainty_bands(df, forecast_horizon=20.0) is None

    def test_no_matching_horizon_is_unavailable(self):
        df = pd.DataFrame({"horizon_hours": [30.0], "error_mw": [100.0]})
        assert compute_uncertainty_bands(df, forecast_horizon=10.0) is None
