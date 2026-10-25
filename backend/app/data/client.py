"""Elexon BMRS stream client with bounded date windows, retries, and rate limiting."""

import asyncio
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import settings

logger = logging.getLogger(__name__)


class ElexonClient:
    """Client for the Elexon BMRS Insights Solution API.

    The stream endpoints return arrays rather than paginated envelopes, so
    requests are partitioned into bounded date windows instead.
    """

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or settings.elexon_base_url
        self._rate_limit = settings.elexon_rate_limit_per_second
        self._last_request_time: float = 0

    async def _rate_limited_delay(self) -> None:
        """Enforce rate limiting between requests."""
        now = asyncio.get_running_loop().time()
        elapsed = now - self._last_request_time
        min_interval = 1.0 / max(self._rate_limit, 0.01)
        if elapsed < min_interval:
            await asyncio.sleep(min_interval - elapsed)
        self._last_request_time = asyncio.get_running_loop().time()

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.ConnectError, httpx.TimeoutException)),
    )
    async def _get(self, endpoint: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Make a GET request with retries and rate limiting."""
        await self._rate_limited_delay()
        url = f"{self.base_url}{endpoint}"
        logger.info(f"GET {url} params={params}")

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        if isinstance(data, list):
            return data
        # Some endpoints might wrap in an object
        if isinstance(data, dict) and "data" in data:
            records = data["data"]
            if isinstance(records, list):
                return records
        raise ValueError(f"Unexpected response shape from {url}: {type(data).__name__}")

    async def fetch_fuelhh_wind(
        self,
        start_date: date,
        end_date: date,
    ) -> List[Dict[str, Any]]:
        """Fetch half-hourly actual wind generation (FUELHH).

        Uses settlementDate range filtering and filters for fuelType=WIND.
        Fetches in bounded weekly chunks to manage response sizes.

        Args:
            start_date: First settlement date (inclusive)
            end_date: Last settlement date (inclusive)

        Returns:
            List of WIND generation records
        """
        all_records: List[Dict[str, Any]] = []
        current = start_date

        while current <= end_date:
            # A week is small enough for FUELHH and reduces request overhead.
            chunk_end = min(current + timedelta(days=6), end_date)
            params = {
                "settlementDateFrom": current.isoformat(),
                "settlementDateTo": chunk_end.isoformat(),
                "fuelType": "WIND",
            }

            try:
                records = await self._get("/datasets/FUELHH/stream", params)
                wind_records = [r for r in records if r.get("fuelType") == "WIND"]
                all_records.extend(wind_records)
                logger.info(
                    f"FUELHH {current} to {chunk_end}: "
                    f"{len(records)} total, {len(wind_records)} WIND"
                )
            except Exception as e:
                logger.error(f"Failed to fetch FUELHH {current} to {chunk_end}: {e}")
                raise

            current = chunk_end + timedelta(days=1)

        logger.info(f"Total FUELHH WIND records fetched: {len(all_records)}")
        return all_records

    async def fetch_windfor(
        self,
        publish_from: datetime,
        publish_to: datetime,
    ) -> List[Dict[str, Any]]:
        """Fetch wind generation forecasts (WINDFOR).

        Uses publishDateTime range filtering. Fetches in 6-hour chunks
        because the volume of forecast data is very high (many publish
        times per target time).

        Args:
            publish_from: Start of publish window (UTC)
            publish_to: End of publish window (UTC)

        Returns:
            List of forecast records
        """
        all_records: List[Dict[str, Any]] = []
        publish_from = publish_from.astimezone(timezone.utc)
        publish_to = publish_to.astimezone(timezone.utc)
        current = publish_from
        chunk_hours = 6  # Stream responses are arrays and have no page token.

        while current < publish_to:
            chunk_end = min(current + timedelta(hours=chunk_hours), publish_to)
            params = {
                "publishDateTimeFrom": current.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "publishDateTimeTo": chunk_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
            }

            try:
                records = await self._get("/datasets/WINDFOR/stream", params)
                all_records.extend(records)
                logger.info(
                    f"WINDFOR {current.isoformat()} to {chunk_end.isoformat()}: "
                    f"{len(records)} records"
                )
            except Exception as e:
                logger.error(
                    f"Failed to fetch WINDFOR {current.isoformat()} "
                    f"to {chunk_end.isoformat()}: {e}"
                )
                raise

            current = chunk_end

        logger.info(f"Total WINDFOR records fetched: {len(all_records)}")
        return all_records
