"""Tests for bounded Elexon publication-window fetching."""

from datetime import datetime, timedelta, timezone

import pytest

from app.data.client import ElexonClient


@pytest.mark.asyncio
async def test_windfor_windows_cover_the_full_range_without_skipping():
    client = ElexonClient()
    client._rate_limit = 1000
    calls = []

    async def fake_get(endpoint, params):
        calls.append((endpoint, params))
        return []

    client._get = fake_get
    start = datetime(2025, 12, 31, 0, 0, tzinfo=timezone.utc)
    end = start + timedelta(hours=18)

    await client.fetch_windfor(start, end)

    assert len(calls) == 3
    windows = [
        (params["publishDateTimeFrom"], params["publishDateTimeTo"])
        for _, params in calls
    ]
    assert windows == [
        ("2025-12-31T00:00:00Z", "2025-12-31T06:00:00Z"),
        ("2025-12-31T06:00:00Z", "2025-12-31T12:00:00Z"),
        ("2025-12-31T12:00:00Z", "2025-12-31T18:00:00Z"),
    ]


@pytest.mark.asyncio
async def test_windfor_normalizes_non_utc_input_before_querying():
    client = ElexonClient()
    client._rate_limit = 1000
    calls = []

    async def fake_get(endpoint, params):
        calls.append(params)
        return []

    client._get = fake_get
    start = datetime.fromisoformat("2025-12-31T01:00:00+01:00")
    await client.fetch_windfor(start, start + timedelta(hours=1))

    assert calls[0]["publishDateTimeFrom"] == "2025-12-31T00:00:00Z"
    assert calls[0]["publishDateTimeTo"] == "2025-12-31T01:00:00Z"
