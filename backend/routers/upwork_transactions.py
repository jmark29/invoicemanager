"""Endpoints for Upwork transactions (CRUD + XLSX import)."""

import shutil
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import get_db
from backend.models.import_history import ImportHistory
from backend.models.upwork_transaction import UpworkTransaction
from backend.schemas.import_history import ImportHistoryResponse
from backend.schemas.upwork_transaction import (
    UpworkImportResponse,
    UpworkTransactionResponse,
    UpworkTransactionUpdate,
)
from backend.services.file_validation import validate_xlsx
from backend.services.upwork_import import import_upwork_transactions

router = APIRouter(prefix="/api/upwork-transactions", tags=["upwork-transactions"])


@router.get("", response_model=list[UpworkTransactionResponse])
def list_upwork_transactions(
    assigned_month: str | None = None,
    category_id: str | None = None,
    skip: int = 0,
    limit: int = 500,
    db: Session = Depends(get_db),
):
    query = db.query(UpworkTransaction)
    if assigned_month:
        query = query.filter(UpworkTransaction.assigned_month == assigned_month)
    if category_id:
        query = query.filter(UpworkTransaction.category_id == category_id)
    return query.order_by(UpworkTransaction.tx_date.desc()).offset(skip).limit(limit).all()


@router.get("/{tx_id}", response_model=UpworkTransactionResponse)
def get_upwork_transaction(tx_id: int, db: Session = Depends(get_db)):
    tx = db.get(UpworkTransaction, tx_id)
    if not tx:
        raise HTTPException(404, f"Upwork transaction {tx_id} not found")
    return tx


@router.patch("/{tx_id}", response_model=UpworkTransactionResponse)
def update_upwork_transaction(
    tx_id: int, data: UpworkTransactionUpdate, db: Session = Depends(get_db)
):
    tx = db.get(UpworkTransaction, tx_id)
    if not tx:
        raise HTTPException(404, f"Upwork transaction {tx_id} not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(tx, key, value)
    db.commit()
    db.refresh(tx)
    return tx


@router.post("/import", response_model=UpworkImportResponse)
def import_upwork_xlsx(
    file: UploadFile,
    category_id: str | None = None,
    db: Session = Depends(get_db),
):
    """Import Upwork transactions from an XLSX file."""
    validate_xlsx(file)

    # Save uploaded file with timestamped name for history
    imports_dir = settings.IMPORTS_DIR
    imports_dir.mkdir(parents=True, exist_ok=True)
    original_filename = file.filename or "upwork_import.xlsx"
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    stored_name = f"upwork_{ts}_{original_filename}"
    stored_path = imports_dir / stored_name

    with open(stored_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    result = import_upwork_transactions(str(stored_path), db, category_id=category_id)

    # Record import history
    history = ImportHistory(
        file_type="upwork",
        original_filename=original_filename,
        stored_path=f"imports/{stored_name}",
        record_count=result.imported,
        skipped_count=result.skipped_duplicate,
        notes="; ".join(result.errors) if result.errors else None,
    )
    db.add(history)
    db.commit()

    return UpworkImportResponse(
        imported=result.imported,
        skipped_duplicate=result.skipped_duplicate,
        skipped_no_amount=result.skipped_no_amount,
        skipped_no_period=result.skipped_no_period,
        errors=result.errors,
    )


@router.get("/import-history", response_model=list[ImportHistoryResponse])
def list_upwork_import_history(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """List import history for Upwork transaction imports."""
    return (
        db.query(ImportHistory)
        .filter(ImportHistory.file_type == "upwork")
        .order_by(ImportHistory.imported_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
