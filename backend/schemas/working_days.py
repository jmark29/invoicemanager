"""Pydantic schemas for working days responses."""

from pydantic import BaseModel


class WorkingDaysResponse(BaseModel):
    year: int
    month: int
    working_days: int
    holidays: list[str]  # ISO date strings of holidays in that month
