"""Elexon BMRS API client with pagination, retries, and rate limiting."""

import httpx
import asyncio
import logging
from datetime import datetime, timedelta, date
from typing import List, Dict, Any, Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import settings

logger = logging.getLogger(__name__)


class ElexonClient:
    """Client for the Elexon BMRS Insights Solution API.

    Handles pagination via date windowing (the stream endpoints return
    all data without pagination, but we chunk requests by date to manage
    response sizes and respect rate limits).
    """

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or settings.elexon_base_url
        self._rate_limit = settings.elexon_rate_limit_per_second
        self._last_request_time: float = 0

    async def _rate_limited_delay(self) -> None:
        """Enforce rate limiting between requests."""
        now = asyncio.get_event_loop().time()
        elapsed = now - self._last_request_time
        min_interval = 1.0 / self._rate_limit
        if elapsed < min_interval:
            await asyncio.sleep(min_interval - elapsed)
        self._last_request_time = asyncio.get_event_loop().time()

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
            return data["data"]
        return data if isinstance(data, list) else [data]

    async def fetch_fuelhh_wind(
        self,
        start_date: date,
        end_date: date,
    ) -> List[Dict[str, Any]]:
        """Fetch half-hourly actual wind generation (FUELHH).

        Uses settlementDate range filtering and filters for fuelType=WIND.
        Fetches in daily chunks to manage response sizes.

        Args:
            start_date: First settlement date (inclusive)
            end_date: Last settlement date (inclusive)

        Returns:
            List of WIND generation records
        """
        all_records: List[Dict[str, Any]] = []
        current = start_date

        while current <= end_date:
            # Fetch one day at a time
            chunk_end = min(current + timedelta(days=6), end_date)
            params = {
                "settlementDateFrom": current.isoformat(),
                "settlementDateTo": chunk_end.isoformat(),
            }

            try:
                records = await self._get("/datasets/FUELHH/stream", params)
                # Filter for WIND fuel type
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
        current = publish_from
        chunk_hours = 6  # 6-hour chunks to manage response size

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
