"""CLI script to fetch and cache Elexon BMRS data.

Usage:
    python -m app.data.fetch_data [--force]

Fetches FUELHH (actuals) and WINDFOR (forecasts) for January 2026
and stores them in the local SQLite cache.
"""

import asyncio
import argparse
import logging
import sys
from datetime import datetime, date, timedelta

from app.data.client import ElexonClient
from app.data.cache import DataCache
from app.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def fetch_actuals(client: ElexonClient, cache: DataCache) -> int:
    """Fetch and cache FUELHH WIND actuals for January 2026."""
    logger.info("Fetching FUELHH WIND actuals for January 2026...")
    start = date.fromisoformat(settings.scope_start)
    end = date.fromisoformat(settings.scope_end)

    records = await client.fetch_fuelhh_wind(start, end)
    count = cache.save_actuals(records)
    logger.info(f"Cached {count} actual records")
    return count


async def fetch_forecasts(client: ElexonClient, cache: DataCache) -> int:
    """Fetch and cache WINDFOR forecasts.

    Fetches from mid-December 2025 through end of January 2026
    to capture early forecasts for January targets.
    Only keeps forecast rows where startTime is in January 2026.
    """
    logger.info("Fetching WINDFOR forecasts...")
    publish_from = datetime.fromisoformat(f"{settings.forecast_fetch_start}T00:00:00+00:00")
    publish_to = datetime.fromisoformat(f"{settings.scope_end}T23:59:59+00:00")

    records = await client.fetch_windfor(publish_from, publish_to)

    # Filter: only keep forecasts targeting January 2026
    scope_start = settings.scope_start
    scope_end = settings.scope_end
    jan_records = []
    for r in records:
        st = r.get("startTime", "")
        # startTime is like "2026-01-01T00:00:00Z"
        if st >= f"{scope_start}T00:00:00" and st <= f"{scope_end}T23:59:59":
            jan_records.append(r)

    logger.info(
        f"Filtered to {len(jan_records)} records targeting Jan 2026 "
        f"(from {len(records)} total)"
    )
    count = cache.save_forecasts(jan_records)
    logger.info(f"Cached {count} forecast records")
    return count


async def main(force: bool = False) -> None:
    """Main fetch routine."""
    cache_inst = DataCache()

    if not force and cache_inst.has_data():
        meta = cache_inst.get_metadata()
        logger.info(
            f"Cache already has data: "
            f"{meta.get('actuals_count', 0)} actuals, "
            f"{meta.get('forecasts_count', 0)} forecasts. "
            f"Use --force to re-fetch."
        )
        return

    client = ElexonClient()

    logger.info("=" * 60)
    logger.info("Starting data fetch from Elexon BMRS")
    logger.info("=" * 60)

    actuals_count = await fetch_actuals(client, cache_inst)
    forecasts_count = await fetch_forecasts(client, cache_inst)

    logger.info("=" * 60)
    logger.info(
        f"Fetch complete: {actuals_count} actuals, {forecasts_count} forecasts"
    )
    logger.info("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch and cache Elexon BMRS data")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-fetch even if cache has data",
    )
    args = parser.parse_args()
    asyncio.run(main(force=args.force))
