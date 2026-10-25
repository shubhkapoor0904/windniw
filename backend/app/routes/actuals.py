"""Actuals endpoint: half-hourly wind generation outturn data."""

from fastapi import APIRouter, Query, HTTPException
from datetime import date
from typing import Optional

from app.models import ActualRecord, ActualsResponse
from app.data.cache import cache

router = APIRouter()


@router.get("/actuals", response_model=ActualsResponse)
async def get_actuals(
    start: Optional[str] = Query(
        "2026-01-01",
        description="Start date (YYYY-MM-DD), must be in January 2026",
    ),
    end: Optional[str] = Query(
        "2026-01-31",
        description="End date (YYYY-MM-DD), must be in January 2026",
    ),
) -> ActualsResponse:
    """Get actual wind generation data for a date range.

    Data is from the FUELHH dataset, filtered for WIND fuel type.
    Restricted to January 2026.
    """
    # Validate dates
    try:
        start_date = date.fromisoformat(start) if start else date(2026, 1, 1)
        end_date = date.fromisoformat(end) if end else date(2026, 1, 31)
    except ValueError:
        raise HTTPException(400, "Invalid date format. Use YYYY-MM-DD.")

    if start_date < date(2026, 1, 1) or end_date > date(2026, 1, 31):
        raise HTTPException(400, "Dates must be within January 2026.")

    if start_date > end_date:
        raise HTTPException(400, "start must be before or equal to end.")

    df = cache.get_actuals(start_date.isoformat(), end_date.isoformat())

    data = [
        ActualRecord(
            start_time=row["start_time"],
            settlement_date=date.fromisoformat(row["settlement_date"]),
            settlement_period=row["settlement_period"],
            generation_mw=row["generation_mw"],
        )
        for _, row in df.iterrows()
    ]

    return ActualsResponse(data=data, count=len(data))
