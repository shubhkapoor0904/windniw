"""Tests for accuracy metrics."""

import pandas as pd
import numpy as np

from app.analytics.metrics import (
    compute_error,
    compute_mae,
    compute_rmse,
    compute_mape,
    compute_bias,
    compute_percentiles,
    compute_nmae,
    compute_all_metrics,
    compute_error_distribution,
)


class TestComputeError:
    """Tests for error computation."""

    def test_positive_error_means_over_forecast(self):
        """forecast > actual → positive error."""
        forecast = pd.Series([100.0])
        actual = pd.Series([80.0])
        error = compute_error(forecast, actual)
        assert error.iloc[0] == 20.0

    def test_negative_error_means_under_forecast(self):
        """forecast < actual → negative error."""
        forecast = pd.Series([80.0])
        actual = pd.Series([100.0])
        error = compute_error(forecast, actual)
        assert error.iloc[0] == -20.0

    def test_zero_error(self):
        """Perfect forecast → zero error."""
        vals = pd.Series([50.0, 100.0, 150.0])
        error = compute_error(vals, vals)
        assert (error == 0).all()


class TestMAE:
    def test_basic_mae(self):
        errors = pd.Series([10, -20, 30, -40])
        assert compute_mae(errors) == 25.0

    def test_perfect_forecast(self):
        errors = pd.Series([0, 0, 0])
        assert compute_mae(errors) == 0.0


class TestRMSE:
    def test_basic_rmse(self):
        errors = pd.Series([3.0, -4.0])
        # RMSE = sqrt((9 + 16) / 2) = sqrt(12.5) ≈ 3.536
        assert abs(compute_rmse(errors) - 3.536) < 0.01

    def test_single_error(self):
        errors = pd.Series([5.0])
        assert compute_rmse(errors) == 5.0


class TestMAPE:
    def test_basic_mape(self):
        forecast = pd.Series([110.0, 90.0])
        actual = pd.Series([100.0, 100.0])
        mape = compute_mape(forecast, actual)
        assert mape == 10.0  # 10% each

    def test_zero_actual_excluded(self):
        """Zero actuals should be excluded from MAPE calculation."""
        forecast = pd.Series([10.0, 100.0])
        actual = pd.Series([0.0, 100.0])
        mape = compute_mape(forecast, actual, zero_threshold=1.0)
        assert mape == 0.0  # Only the 100/100 pair counted

    def test_all_zero_returns_none(self):
        forecast = pd.Series([10.0])
        actual = pd.Series([0.0])
        assert compute_mape(forecast, actual) is None


class TestBias:
    def test_positive_bias(self):
        """All over-forecasts → positive bias."""
        errors = pd.Series([10, 20, 30])
        assert compute_bias(errors) == 20.0

    def test_unbiased(self):
        """Symmetric errors → zero bias."""
        errors = pd.Series([10, -10, 20, -20])
        assert compute_bias(errors) == 0.0


class TestPercentiles:
    def test_basic_percentiles(self):
        errors = pd.Series(range(-50, 51))
        pcts = compute_percentiles(errors, [50, 90, 99])
        assert "p50" in pcts
        assert "p90" in pcts
        assert "p99" in pcts
        # P50 of absolute values of -50 to 50 should be ~25
        assert abs(pcts["p50"] - 25) < 2


class TestNMAE:
    def test_basic_nmae(self):
        errors = pd.Series([10, -10])
        actuals = pd.Series([100, 100])
        # MAE = 10, mean_actual = 100, nMAE = 10%
        assert compute_nmae(errors, actuals) == 10.0

    def test_zero_actual_returns_none(self):
        errors = pd.Series([1.0])
        actuals = pd.Series([0.0])
        assert compute_nmae(errors, actuals) is None


class TestComputeAllMetrics:
    def test_returns_all_keys(self):
        forecast = pd.Series([100, 110, 90, 105])
        actual = pd.Series([100, 100, 100, 100])
        result = compute_all_metrics(forecast, actual)

        expected_keys = [
            "mae", "rmse", "mape", "bias",
            "p50_abs_error", "p90_abs_error", "p99_abs_error",
            "nmae", "count",
        ]
        for key in expected_keys:
            assert key in result

    def test_count_matches(self):
        forecast = pd.Series([100, 110, np.nan, 105])
        actual = pd.Series([100, 100, 100, np.nan])
        result = compute_all_metrics(forecast, actual)
        assert result["count"] == 2  # Only 2 valid pairs

    def test_missing_pairs_are_not_reported_as_zero_accuracy(self):
        result = compute_all_metrics(pd.Series([np.nan]), pd.Series([10.0]))
        assert result["count"] == 0
        assert result["mae"] is None
        assert result["bias"] is None
        assert result["mape"] is None


class TestErrorDistribution:
    def test_histogram_structure(self):
        errors = pd.Series(np.random.randn(100) * 50)
        dist = compute_error_distribution(errors, n_bins=10)
        assert len(dist) == 10
        assert all("bin_start" in d and "bin_end" in d and "count" in d for d in dist)

    def test_empty_returns_empty(self):
        errors = pd.Series([], dtype=float)
        assert compute_error_distribution(errors) == []

    def test_all_missing_returns_empty(self):
        errors = pd.Series([np.nan, np.nan])
        assert compute_error_distribution(errors) == []
