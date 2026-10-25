"""Horizon analysis: how forecast error changes with lead time.

Groups forecast errors by horizon bucket and computes per-bucket metrics.
This helps buyers answer: "How much should I trust a forecast made X hours ahead?"
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Tuple, Optional

# Default horizon buckets (hours)
DEFAULT_HORIZON_BUCKETS: List[Tuple[float, float, str]] = [
    (0, 6, "0-6h"),
    (6, 12, "6-12h"),
    (12, 24, "12-24h"),
    (24, 36, "24-36h"),
    (36, 48, "36-48h"),
    (48, 72, "48-72h"),
    (72, float("inf"), "72h+"),
]


def assign_horizon_bucket(
    horizon_hours: float,
    buckets: Optional[List[Tuple[float, float, str]]] = None,
) -> Optional[str]:
    """Assign a horizon value to a bucket label.

    Args:
        horizon_hours: Forecast horizon in hours
        buckets: List of (min, max, label) tuples. Uses defaults if None.

    Returns:
        Bucket label string, or None if not matched
    """
    if buckets is None:
        buckets = DEFAULT_HORIZON_BUCKETS

    for min_h, max_h, label in buckets:
        if min_h <= horizon_hours < max_h:
            return label
    return None


def compute_horizon_metrics(
    df: pd.DataFrame,
    buckets: Optional[List[Tuple[float, float, str]]] = None,
) -> List[Dict[str, Any]]:
    """Compute error metrics grouped by forecast horizon bucket.

    Args:
        df: DataFrame with columns [horizon_hours, error_mw]
            where error_mw = forecast - actual
        buckets: Custom horizon buckets. Uses defaults if None.

    Returns:
        List of dicts, one per bucket, with metrics
    """
    if buckets is None:
        buckets = DEFAULT_HORIZON_BUCKETS

    if df.empty or "horizon_hours" not in df.columns or "error_mw" not in df.columns:
        return []

    df = df[["horizon_hours", "error_mw"]].dropna()
    df = df[np.isfinite(df["horizon_hours"]) & np.isfinite(df["error_mw"])]
    if df.empty:
        return []

    results = []
    for min_h, max_h, label in buckets:
        mask = (df["horizon_hours"] >= min_h) & (df["horizon_hours"] < max_h)
        bucket_data = df[mask]

        if bucket_data.empty:
            continue

        errors = bucket_data["error_mw"]
        abs_errors = errors.abs()

        results.append({
            "horizon_label": label,
            "horizon_min_hours": min_h,
            "horizon_max_hours": min(max_h, 999),  # Cap infinity for JSON
            "mae": round(float(abs_errors.mean()), 2),
            "rmse": round(float(np.sqrt((errors**2).mean())), 2),
            "bias": round(float(errors.mean()), 2),
            "p10_error": round(float(errors.quantile(0.10)), 2),
            "p90_error": round(float(errors.quantile(0.90)), 2),
            "count": int(len(bucket_data)),
        })

    return results


def compute_uncertainty_bands(
    df: pd.DataFrame,
    forecast_horizon: float,
    buckets: Optional[List[Tuple[float, float, str]]] = None,
) -> Optional[Tuple[float, float]]:
    """Compute P10/P90 error bands for a given forecast horizon.

    Used to generate uncertainty bands around the latest forecast.
    The band represents the plausible range of actual generation:
    - Lower = forecast + P10 of historical error (error = forecast - actual)
    - Upper = forecast + P90 of historical error

    Since error = forecast - actual:
    - If error is positive, forecast was too high → actual was lower
    - P10 of error is typically negative (under-forecast cases)
    - P90 of error is typically positive (over-forecast cases)

    So the actual plausible range is:
    - actual_low  = forecast - P90_of_error  (worst case: forecast over-shot)
    - actual_high = forecast - P10_of_error  (worst case: forecast under-shot)

    Args:
        df: DataFrame with columns [horizon_hours, error_mw]
        forecast_horizon: The horizon of the forecast to band
        buckets: Custom horizon buckets

    Returns:
        Tuple of (P10_error, P90_error), or None if the horizon has no history
    """
    if buckets is None:
        buckets = DEFAULT_HORIZON_BUCKETS

    if df.empty:
        return None

    # Find the matching bucket
    for min_h, max_h, label in buckets:
        if min_h <= forecast_horizon < max_h:
            mask = (df["horizon_hours"] >= min_h) & (df["horizon_hours"] < max_h)
            bucket_data = df[mask]
            bucket_data = bucket_data.dropna(subset=["error_mw"])
            if bucket_data.empty:
                return None
            errors = bucket_data["error_mw"]
            return (
                round(float(errors.quantile(0.10)), 2),
                round(float(errors.quantile(0.90)), 2),
            )

    return None
