"""Working days endpoint."""

from fastapi import APIRouter

from backend.schemas.working_days import WorkingDaysResponse
from backend.services.working_days import hessen_holidays, working_days_in_month

router = APIRouter(prefix="/api/working-days", tags=["working-days"])


@router.get("/{year}/{month}", response_model=WorkingDaysResponse)
def get_working_days(year: int, month: int):
    if month < 1 or month > 12:
        from fastapi import HTTPException

        raise HTTPException(400, "Month must be between 1 and 12")

    count = working_days_in_month(year, month)
    holidays = hessen_holidays(year)

    # Filter holidays to the requested month
    month_holidays = sorted(
        h.isoformat() for h in holidays if h.month == month
    )

    return WorkingDaysResponse(
        year=year,
        month=month,
        working_days=count,
        holidays=month_holidays,
    )
