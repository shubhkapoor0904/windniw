"""SQLite-based cache for raw Elexon BMRS data.

Stores actuals (FUELHH WIND) and forecasts (WINDFOR) in a local SQLite
database so the app doesn't hit Elexon on every request.
"""

import sqlite3
import json
import os
import logging
from datetime import datetime, date
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

import pandas as pd

from app.config import settings

logger = logging.getLogger(__name__)


class DataCache:
    """SQLite cache for wind generation data."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or settings.cache_db
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Create tables if they don't exist."""
        conn = self._get_conn()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS actuals (
                    start_time TEXT NOT NULL,
                    settlement_date TEXT NOT NULL,
                    settlement_period INTEGER NOT NULL,
                    generation_mw REAL NOT NULL,
                    PRIMARY KEY (start_time)
                );

                CREATE TABLE IF NOT EXISTS forecasts (
                    start_time TEXT NOT NULL,
                    publish_time TEXT NOT NULL,
                    generation_mw REAL NOT NULL,
                    PRIMARY KEY (start_time, publish_time)
                );

                CREATE INDEX IF NOT EXISTS idx_forecasts_start
                    ON forecasts(start_time);
                CREATE INDEX IF NOT EXISTS idx_forecasts_publish
                    ON forecasts(publish_time);
                CREATE INDEX IF NOT EXISTS idx_actuals_date
                    ON actuals(settlement_date);

                CREATE TABLE IF NOT EXISTS fetch_metadata (
                    dataset TEXT PRIMARY KEY,
                    last_fetched TEXT,
                    record_count INTEGER
                );
            """)
            conn.commit()
        finally:
            conn.close()

    # ─── Write ─────────────────────────────────────────────

    def save_actuals(self, records: List[Dict[str, Any]]) -> int:
        """Save FUELHH WIND records to cache.

        Args:
            records: Raw API response records

        Returns:
            Number of records inserted/updated
        """
        conn = self._get_conn()
        count = 0
        try:
            for r in records:
                start_time = r.get("startTime", "")
                settlement_date = r.get("settlementDate", "")
                settlement_period = r.get("settlementPeriod", 0)
                generation = r.get("generation", 0.0)

                conn.execute(
                    """INSERT OR REPLACE INTO actuals
                       (start_time, settlement_date, settlement_period, generation_mw)
                       VALUES (?, ?, ?, ?)""",
                    (start_time, settlement_date, settlement_period, generation),
                )
                count += 1

            # Update metadata
            conn.execute(
                """INSERT OR REPLACE INTO fetch_metadata (dataset, last_fetched, record_count)
                   VALUES (?, ?, ?)""",
                ("FUELHH_WIND", datetime.utcnow().isoformat(), count),
            )
            conn.commit()
            logger.info(f"Saved {count} actual records to cache")
        finally:
            conn.close()
        return count

    def save_forecasts(self, records: List[Dict[str, Any]]) -> int:
        """Save WINDFOR records to cache.

        Args:
            records: Raw API response records

        Returns:
            Number of records inserted/updated
        """
        conn = self._get_conn()
        count = 0
        try:
            for r in records:
                start_time = r.get("startTime", "")
                publish_time = r.get("publishTime", "")
                generation = r.get("generation", 0.0)

                conn.execute(
                    """INSERT OR REPLACE INTO forecasts
                       (start_time, publish_time, generation_mw)
                       VALUES (?, ?, ?)""",
                    (start_time, publish_time, generation),
                )
                count += 1

            conn.execute(
                """INSERT OR REPLACE INTO fetch_metadata (dataset, last_fetched, record_count)
                   VALUES (?, ?, ?)""",
                ("WINDFOR", datetime.utcnow().isoformat(), count),
            )
            conn.commit()
            logger.info(f"Saved {count} forecast records to cache")
        finally:
            conn.close()
        return count

    # ─── Read ──────────────────────────────────────────────

    def get_actuals(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """Load actuals from cache as DataFrame.

        Args:
            start_date: Filter by settlement_date >= (YYYY-MM-DD)
            end_date: Filter by settlement_date <= (YYYY-MM-DD)

        Returns:
            DataFrame with columns: start_time, settlement_date, settlement_period, generation_mw
        """
        conn = self._get_conn()
        try:
            query = "SELECT * FROM actuals"
            conditions = []
            params = []

            if start_date:
                conditions.append("settlement_date >= ?")
                params.append(start_date)
            if end_date:
                conditions.append("settlement_date <= ?")
                params.append(end_date)

            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            query += " ORDER BY start_time"

            df = pd.read_sql_query(query, conn, params=params)

            if not df.empty:
                df["start_time"] = pd.to_datetime(df["start_time"], utc=True)

            return df
        finally:
            conn.close()

    def get_forecasts(
        self,
        target_start: Optional[str] = None,
        target_end: Optional[str] = None,
        publish_before: Optional[str] = None,
    ) -> pd.DataFrame:
        """Load forecasts from cache as DataFrame.

        Args:
            target_start: Filter by start_time >= (ISO datetime)
            target_end: Filter by start_time <= (ISO datetime)
            publish_before: Filter by publish_time <= (ISO datetime)

        Returns:
            DataFrame with columns: start_time, publish_time, generation_mw
        """
        conn = self._get_conn()
        try:
            query = "SELECT * FROM forecasts"
            conditions = []
            params = []

            if target_start:
                conditions.append("start_time >= ?")
                params.append(target_start)
            if target_end:
                conditions.append("start_time <= ?")
                params.append(target_end)
            if publish_before:
                conditions.append("publish_time <= ?")
                params.append(publish_before)

            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            query += " ORDER BY start_time, publish_time"

            df = pd.read_sql_query(query, conn, params=params)

            if not df.empty:
                df["start_time"] = pd.to_datetime(df["start_time"], utc=True)
                df["publish_time"] = pd.to_datetime(df["publish_time"], utc=True)

            return df
        finally:
            conn.close()

    # ─── Meta ──────────────────────────────────────────────

    def get_metadata(self) -> Dict[str, Any]:
        """Get cache metadata (counts, dates, etc.)."""
        conn = self._get_conn()
        try:
            meta: Dict[str, Any] = {}

            # Counts
            row = conn.execute("SELECT COUNT(*) as cnt FROM actuals").fetchone()
            meta["actuals_count"] = row["cnt"] if row else 0

            row = conn.execute("SELECT COUNT(*) as cnt FROM forecasts").fetchone()
            meta["forecasts_count"] = row["cnt"] if row else 0

            # Date ranges
            row = conn.execute(
                "SELECT MIN(start_time) as mn, MAX(start_time) as mx FROM actuals"
            ).fetchone()
            if row and row["mn"]:
                meta["actuals_date_range"] = [row["mn"], row["mx"]]

            row = conn.execute(
                "SELECT MIN(publish_time) as mn, MAX(publish_time) as mx FROM forecasts"
            ).fetchone()
            if row and row["mn"]:
                meta["forecasts_publish_range"] = [row["mn"], row["mx"]]

            row = conn.execute(
                "SELECT MIN(start_time) as mn, MAX(start_time) as mx FROM forecasts"
            ).fetchone()
            if row and row["mn"]:
                meta["forecasts_target_range"] = [row["mn"], row["mx"]]

            # Last fetched
            rows = conn.execute("SELECT * FROM fetch_metadata").fetchall()
            for r in rows:
                meta[f"{r['dataset']}_last_fetched"] = r["last_fetched"]

            # Cache size
            if os.path.exists(self.db_path):
                meta["cache_size_mb"] = round(
                    os.path.getsize(self.db_path) / (1024 * 1024), 2
                )

            return meta
        finally:
            conn.close()

    def has_data(self) -> bool:
        """Check if cache has any data loaded."""
        meta = self.get_metadata()
        return meta.get("actuals_count", 0) > 0 and meta.get("forecasts_count", 0) > 0


# Global cache instance
cache = DataCache()
