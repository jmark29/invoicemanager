"""Endpoints for company settings (singleton)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.company_settings import CompanySettings
from backend.schemas.company_settings import CompanySettingsResponse, CompanySettingsUpdate

router = APIRouter(prefix="/api/settings", tags=["settings"])


def _get_or_create_settings(db: Session) -> CompanySettings:
    """Return the singleton CompanySettings row, creating it if needed."""
    settings = db.get(CompanySettings, 1)
    if not settings:
        settings = CompanySettings(id=1)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


@router.get("/company", response_model=CompanySettingsResponse)
def get_company_settings(db: Session = Depends(get_db)):
    return _get_or_create_settings(db)


@router.patch("/company", response_model=CompanySettingsResponse)
def update_company_settings(data: CompanySettingsUpdate, db: Session = Depends(get_db)):
    settings = _get_or_create_settings(db)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(settings, key, value)
    db.commit()
    db.refresh(settings)
    return settings
