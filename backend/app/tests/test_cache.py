"""Tests for cache filtering and UTC timestamp normalization."""

import json
import sqlite3

from app.data.cache import DataCache


def test_forecast_filters_include_exact_utc_boundary(tmp_path):
    data_cache = DataCache(str(tmp_path / "test.db"))
    data_cache.save_forecasts([
        {
            "dataset": "WINDFOR",
            "startTime": "2026-01-02T09:00:00Z",
            "publishTime": "2026-01-01T09:00:00Z",
            "generation": 1234,
        }
    ])

    result = data_cache.get_forecasts(
        target_start="2026-01-02T09:00:00+00:00",
        target_end="2026-01-02T09:00:00+00:00",
        publish_before="2026-01-01T09:00:00+00:00",
    )

    assert len(result) == 1
    assert result.iloc[0]["generation_mw"] == 1234


def test_cache_retains_raw_api_record(tmp_path):
    db_path = str(tmp_path / "raw.db")
    data_cache = DataCache(db_path)
    record = {
        "dataset": "WINDFOR",
        "startTime": "2026-01-02T09:00:00Z",
        "publishTime": "2026-01-01T09:00:00Z",
        "generation": 1234,
    }
    data_cache.save_forecasts([record])

    with sqlite3.connect(db_path) as conn:
        raw_json = conn.execute(
            "SELECT raw_json FROM raw_records WHERE dataset = 'WINDFOR'"
        ).fetchone()[0]
    assert json.loads(raw_json) == record
