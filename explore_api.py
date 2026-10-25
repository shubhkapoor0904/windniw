"""Probe the documented Elexon BMRS stream endpoints and summarize January 2026.

Run from the repository root with:
    python explore_api.py
"""

from __future__ import annotations

import argparse
import time
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from typing import Any

import httpx

BASE_URL = "https://data.elexon.co.uk/bmrs/api/v1"
JAN_START = date(2026, 1, 1)
JAN_END = date(2026, 1, 31)
FORECAST_PUBLISH_START = datetime(2025, 12, 15, tzinfo=timezone.utc)
FORECAST_PUBLISH_END = datetime(2026, 2, 1, tzinfo=timezone.utc)


def get_records(
    client: httpx.Client,
    endpoint: str,
    params: dict[str, str],
) -> list[dict[str, Any]]:
    """Get a stream response with bounded retries for throttling/transient errors."""
    for attempt in range(5):
        response = client.get(f"{BASE_URL}{endpoint}", params=params)
        if response.status_code == 429 or response.status_code >= 500:
            retry_after = response.headers.get("Retry-After")
            delay = float(retry_after) if retry_after and retry_after.isdigit() else 2**attempt
            time.sleep(min(delay, 30))
            continue
        response.raise_for_status()
        body = response.json()
        if not isinstance(body, list):
            raise ValueError(f"Expected an array from {endpoint}, got {type(body).__name__}")
        return body
    raise RuntimeError(f"Repeated transient errors from {endpoint}")


def explore_actuals(client: httpx.Client) -> None:
    records = get_records(
        client,
        "/datasets/FUELHH/stream",
        {
            "settlementDateFrom": JAN_START.isoformat(),
            "settlementDateTo": JAN_END.isoformat(),
            "fuelType": "WIND",
        },
    )
    counts = Counter(record["settlementDate"] for record in records)
    timestamps = [record["startTime"] for record in records]
    missing_days = [
        f"2026-01-{day:02d}" for day in range(1, 32)
        if counts[f"2026-01-{day:02d}"] == 0
    ]
    print("FUELHH actuals")
    print(f"  rows: {len(records)}; keys: {sorted(records[0]) if records else []}")
    print(
        f"  unique startTime: {len(set(timestamps))}; duplicate rows: "
        f"{len(timestamps) - len(set(timestamps))}"
    )
    print(
        f"  range: {min(timestamps) if timestamps else 'none'} .. "
        f"{max(timestamps) if timestamps else 'none'}"
    )
    print(f"  dates without WIND outturn: {missing_days}")
    print(f"  days not containing 48 rows: {[(day, n) for day, n in sorted(counts.items()) if n != 48]}")
    if records:
        print(f"  sample: {records[0]}")


def explore_forecasts(client: httpx.Client) -> None:
    current = FORECAST_PUBLISH_START
    chunk = timedelta(hours=6)
    all_rows: list[dict[str, Any]] = []
    sample_rows: list[dict[str, Any]] = []

    while current < FORECAST_PUBLISH_END:
        chunk_end = min(current + chunk, FORECAST_PUBLISH_END)
        rows = get_records(
            client,
            "/datasets/WINDFOR/stream",
            {
                "publishDateTimeFrom": current.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "publishDateTimeTo": chunk_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
        )
        if len(sample_rows) == 0:
            sample_rows = rows
        all_rows.extend(
            row for row in rows
            if f"{JAN_START.isoformat()}T00:00:00Z"
            <= row["startTime"]
            <= f"{JAN_END.isoformat()}T23:59:59Z"
        )
        current = chunk_end
        time.sleep(0.5)

    unique = {
        (row["startTime"], row["publishTime"]): row
        for row in all_rows
    }
    horizons = [
        (
            datetime.fromisoformat(row["startTime"].replace("Z", "+00:00"))
            - datetime.fromisoformat(row["publishTime"].replace("Z", "+00:00"))
        ).total_seconds() / 3600
        for row in unique.values()
    ]
    targets = {row["startTime"] for row in unique.values()}
    print("WINDFOR forecasts")
    print(f"  six-hour sample rows: {len(sample_rows)}")
    print(f"  sample keys: {sorted(sample_rows[0]) if sample_rows else []}")
    print(
        f"  January target rows: {len(all_rows)}; unique (target, publish) pairs: "
        f"{len(unique)}; duplicate rows: {len(all_rows) - len(unique)}"
    )
    print(f"  unique January targets: {len(targets)} of expected 1,488")
    print(f"  distinct publication times in sampled window: {len({r['publishTime'] for r in sample_rows})}")
    print(
        f"  horizon range: {min(horizons):.2f} .. {max(horizons):.2f} hours"
        if horizons else "  horizon range: no January forecasts returned"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=float, default=120)
    args = parser.parse_args()
    with httpx.Client(timeout=args.timeout) as client:
        explore_actuals(client)
        explore_forecasts(client)


if __name__ == "__main__":
    main()
