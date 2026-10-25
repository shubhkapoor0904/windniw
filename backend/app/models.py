"""Pydantic models for API request/response schemas."""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date


# ─── Actuals ───────────────────────────────────────────────

class ActualRecord(BaseModel):
    """A single half-hourly actual wind generation record."""
    start_time: datetime = Field(description="Start of the 30-min interval (UTC)")
    settlement_date: date
    settlement_period: int
    generation_mw: float = Field(description="Actual wind generation in MW")


class ActualsResponse(BaseModel):
    """Response for actuals endpoint."""
    data: List[ActualRecord]
    count: int


# ─── Forecasts ─────────────────────────────────────────────

class ForecastRecord(BaseModel):
    """A single forecast record with publish and target times."""
    start_time: datetime = Field(description="Target delivery time (UTC)")
    publish_time: datetime = Field(description="When this forecast was published (UTC)")
    generation_mw: float = Field(description="Forecasted wind generation in MW")
    horizon_hours: float = Field(description="Hours between publish and target")


class LatestForecastRecord(BaseModel):
    """Latest forecast available at decision cutoff."""
    start_time: datetime
    publish_time: datetime
    generation_mw: float
    horizon_hours: float
    uncertainty_low: Optional[float] = Field(None, description="P10 band (MW)")
    uncertainty_high: Optional[float] = Field(None, description="P90 band (MW)")


class LatestForecastResponse(BaseModel):
    """Response for latest forecast at decision time."""
    target_date: date
    cutoff_time: datetime
    data: List[LatestForecastRecord]
    summary: Optional["ForecastSummary"] = None


class ForecastSummary(BaseModel):
    """Summary statistics for the forecast."""
    peak_mw: float
    min_mw: float
    avg_mw: float
    total_mwh: float = Field(description="Total energy using observed target interval duration")
    avg_horizon_hours: float
    interval_hours: float = Field(description="Observed forecast target interval in hours")


# ─── Comparison ────────────────────────────────────────────

class ComparisonRecord(BaseModel):
    """Hourly forecast compared with the mean of two half-hour actuals."""
    start_time: datetime
    actual_mw: Optional[float]
    forecast_mw: Optional[float]
    publish_time: Optional[datetime]
    horizon_hours: Optional[float]
    error_mw: Optional[float] = Field(None, description="forecast - actual")
    abs_error_mw: Optional[float]


class ComparisonResponse(BaseModel):
    """Response for the comparison endpoint."""
    data: List[ComparisonRecord]
    count: int


# ─── Metrics ───────────────────────────────────────────────

class AccuracyMetrics(BaseModel):
    """Aggregated accuracy metrics."""
    mae: Optional[float] = Field(description="Mean Absolute Error (MW)")
    rmse: Optional[float] = Field(description="Root Mean Square Error (MW)")
    mape: Optional[float] = Field(None, description="Mean Absolute Percentage Error (%)")
    bias: Optional[float] = Field(description="Mean Error / bias (MW), positive = over-forecast")
    p50_abs_error: Optional[float] = Field(description="Median absolute error (MW)")
    p90_abs_error: Optional[float] = Field(description="90th percentile absolute error (MW)")
    p99_abs_error: Optional[float] = Field(description="99th percentile absolute error (MW)")
    nmae: Optional[float] = Field(None, description="Normalized MAE (% of mean actual)")
    count: int = Field(description="Number of data points used")


class MetricsResponse(BaseModel):
    """Response for the metrics endpoint."""
    start_date: date
    end_date: date
    cutoff_hour: int
    cutoff_minute: int = 0
    metrics: AccuracyMetrics
    error_distribution: List["ErrorBucket"]


class ErrorBucket(BaseModel):
    """Histogram bucket for error distribution."""
    bin_start: float
    bin_end: float
    count: int


# ─── Horizon Analysis ─────────────────────────────────────

class HorizonBucket(BaseModel):
    """Metrics for a specific forecast horizon range."""
    horizon_label: str = Field(description="e.g. '0-6h', '6-12h'")
    horizon_min_hours: float
    horizon_max_hours: float
    mae: float
    rmse: float
    bias: float
    p10_error: float = Field(description="10th percentile of error (MW)")
    p90_error: float = Field(description="90th percentile of error (MW)")
    count: int


class HorizonResponse(BaseModel):
    """Response for horizon analysis endpoint."""
    buckets: List[HorizonBucket]


# ─── Meta ──────────────────────────────────────────────────

class MetaResponse(BaseModel):
    """Response for the meta/health endpoint."""
    actuals_count: int
    forecasts_count: int
    actuals_date_range: Optional[List[str]] = None
    forecasts_publish_range: Optional[List[str]] = None
    forecasts_target_range: Optional[List[str]] = None
    last_fetched: Optional[datetime] = None
    cache_size_mb: Optional[float] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "ok"
    data_loaded: bool = False
    actuals_count: int = 0
    forecasts_count: int = 0


# Rebuild models for forward references
LatestForecastResponse.model_rebuild()
MetricsResponse.model_rebuild()
