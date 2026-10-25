"""Accuracy metrics for forecast evaluation.

All metrics are pure functions operating on pandas Series or DataFrames.
Error convention: error = forecast - actual (positive = over-forecast).
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List


def compute_error(
    forecast: pd.Series,
    actual: pd.Series,
) -> pd.Series:
    """Compute forecast error (forecast minus actual).

    Positive error means over-forecasting (forecast > actual).

    Args:
        forecast: Forecast values (MW)
        actual: Actual values (MW)

    Returns:
        Error series (MW)
    """
    return forecast - actual


def compute_mae(errors: pd.Series) -> float:
    """Mean Absolute Error.

    Args:
        errors: Error series (forecast - actual)

    Returns:
        MAE in MW
    """
    return float(errors.dropna().abs().mean()) if errors.notna().any() else 0.0


def compute_rmse(errors: pd.Series) -> float:
    """Root Mean Square Error.

    Args:
        errors: Error series (forecast - actual)

    Returns:
        RMSE in MW
    """
    valid = errors.dropna()
    return float(np.sqrt((valid**2).mean())) if not valid.empty else 0.0


def compute_mape(
    forecast: pd.Series,
    actual: pd.Series,
    zero_threshold: float = 1.0,
) -> Optional[float]:
    """Mean Absolute Percentage Error.

    Guards against zero or near-zero actuals by excluding them.

    Args:
        forecast: Forecast values (MW)
        actual: Actual values (MW)
        zero_threshold: Minimum actual value to include (default 1 MW)

    Returns:
        MAPE as percentage, or None if all actuals are below threshold
    """
    mask = actual.abs() >= zero_threshold
    if mask.sum() == 0:
        return None

    filtered_forecast = forecast[mask]
    filtered_actual = actual[mask]

    ape = ((filtered_forecast - filtered_actual).abs() / filtered_actual.abs()) * 100
    return float(ape.mean())


def compute_bias(errors: pd.Series) -> float:
    """Mean Error (bias).

    Positive = systematic over-forecasting.
    Negative = systematic under-forecasting.

    Args:
        errors: Error series (forecast - actual)

    Returns:
        Bias in MW
    """
    return float(errors.mean())


def compute_percentiles(
    errors: pd.Series,
    percentiles: List[float] = [50, 90, 99],
) -> Dict[str, float]:
    """Compute percentiles of absolute error.

    Args:
        errors: Error series (forecast - actual)
        percentiles: List of percentiles to compute (0-100)

    Returns:
        Dict mapping 'p{N}' to the percentile value
    """
    abs_errors = errors.dropna().abs()
    result = {}
    for p in percentiles:
        key = f"p{int(p)}"
        result[key] = float(abs_errors.quantile(p / 100)) if not abs_errors.empty else 0.0
    return result


def compute_nmae(
    errors: pd.Series,
    actuals: pd.Series,
) -> Optional[float]:
    """Normalized MAE (as percentage of mean actual).

    Args:
        errors: Error series (forecast - actual)
        actuals: Actual values (MW)

    Returns:
        nMAE as percentage, or None if mean actual is zero
    """
    mean_actual = actuals.mean()
    if abs(mean_actual) < 1.0:
        return None
    mae = errors.abs().mean()
    return float((mae / abs(mean_actual)) * 100)


def compute_all_metrics(
    forecast: pd.Series,
    actual: pd.Series,
) -> Dict[str, Any]:
    """Compute all accuracy metrics.

    Args:
        forecast: Forecast values (MW)
        actual: Actual values (MW)

    Returns:
        Dict with all metric values
    """
    # Drop rows where either is NaN
    valid = pd.DataFrame({"forecast": forecast, "actual": actual}).dropna()

    if valid.empty:
        return {
            "mae": None,
            "rmse": None,
            "mape": None,
            "bias": None,
            "p50_abs_error": None,
            "p90_abs_error": None,
            "p99_abs_error": None,
            "nmae": None,
            "count": 0,
        }

    errors = compute_error(valid["forecast"], valid["actual"])
    pcts = compute_percentiles(errors, [50, 90, 99])

    return {
        "mae": round(compute_mae(errors), 2),
        "rmse": round(compute_rmse(errors), 2),
        "mape": round(compute_mape(valid["forecast"], valid["actual"]), 2)
        if compute_mape(valid["forecast"], valid["actual"]) is not None
        else None,
        "bias": round(compute_bias(errors), 2),
        "p50_abs_error": round(pcts["p50"], 2),
        "p90_abs_error": round(pcts["p90"], 2),
        "p99_abs_error": round(pcts["p99"], 2),
        "nmae": round(compute_nmae(errors, valid["actual"]), 2)
        if compute_nmae(errors, valid["actual"]) is not None
        else None,
        "count": len(valid),
    }


def compute_error_distribution(
    errors: pd.Series,
    n_bins: int = 30,
) -> List[Dict[str, Any]]:
    """Compute histogram of error distribution.

    Args:
        errors: Error series (MW)
        n_bins: Number of histogram bins

    Returns:
        List of dicts with bin_start, bin_end, count
    """
    if errors.empty:
        return []

    valid_errors = errors.dropna()
    if valid_errors.empty:
        return []

    counts, bin_edges = np.histogram(valid_errors, bins=n_bins)
    result = []
    for i in range(len(counts)):
        result.append({
            "bin_start": round(float(bin_edges[i]), 2),
            "bin_end": round(float(bin_edges[i + 1]), 2),
            "count": int(counts[i]),
        })
    return result
