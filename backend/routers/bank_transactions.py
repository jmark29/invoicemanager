"""Endpoints for bank transactions (CRUD + XLSX import)."""

import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import get_db
from backend.models.bank_transaction import BankTransaction
from backend.schemas.bank_transaction import (
    BankImportResponse,
    BankTransactionCreate,
    BankTransactionResponse,
    BankTransactionUpdate,
)
from backend.services.bank_import import import_bank_transactions

router = APIRouter(prefix="/api/bank-transactions", tags=["bank-transactions"])


@router.get("", response_model=list[BankTransactionResponse])
def list_bank_transactions(
    category_id: str | None = None,
    provider_invoice_id: int | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(BankTransaction)
    if category_id:
        query = query.filter(BankTransaction.category_id == category_id)
    if provider_invoice_id:
        query = query.filter(BankTransaction.provider_invoice_id == provider_invoice_id)
    return query.order_by(BankTransaction.booking_date.desc()).all()


@router.get("/{tx_id}", response_model=BankTransactionResponse)
def get_bank_transaction(tx_id: int, db: Session = Depends(get_db)):
    tx = db.get(BankTransaction, tx_id)
    if not tx:
        raise HTTPException(404, f"Bank transaction {tx_id} not found")
    return tx


@router.post("", response_model=BankTransactionResponse, status_code=201)
def create_bank_transaction(
    data: BankTransactionCreate, db: Session = Depends(get_db)
):
    tx = BankTransaction(**data.model_dump())
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


@router.patch("/{tx_id}", response_model=BankTransactionResponse)
def update_bank_transaction(
    tx_id: int, data: BankTransactionUpdate, db: Session = Depends(get_db)
):
    tx = db.get(BankTransaction, tx_id)
    if not tx:
        raise HTTPException(404, f"Bank transaction {tx_id} not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(tx, key, value)
    db.commit()
    db.refresh(tx)
    return tx


@router.post("/import", response_model=BankImportResponse)
def import_bank_xlsx(file: UploadFile, db: Session = Depends(get_db)):
    """Import bank transactions from an XLSX file."""
    # Save uploaded file
    imports_dir = settings.IMPORTS_DIR
    imports_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = imports_dir / (file.filename or "bank_import.xlsx")

    with open(tmp_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    result = import_bank_transactions(str(tmp_path), db)
    return BankImportResponse(
        imported=result.imported,
        skipped_duplicate=result.skipped_duplicate,
        auto_matched=result.auto_matched,
        errors=result.errors,
    )
