"""Endpoints for bank transactions (CRUD + XLSX import)."""

import shutil
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import get_db
from backend.models.bank_transaction import BankTransaction
from backend.models.import_history import ImportHistory
from backend.schemas.bank_transaction import (
    BankImportResponse,
    BankTransactionCreate,
    BankTransactionResponse,
    BankTransactionUpdate,
)
from backend.schemas.import_history import ImportHistoryResponse
from backend.schemas.matching import MatchAction, MatchActionResponse, ManualMatchRequest
from backend.services.bank_import import import_bank_transactions
from backend.services.file_validation import validate_xlsx
from backend.services.transaction_matching import apply_match, reject_match

router = APIRouter(prefix="/api/bank-transactions", tags=["bank-transactions"])


@router.get("", response_model=list[BankTransactionResponse])
def list_bank_transactions(
    category_id: str | None = None,
    provider_invoice_id: int | None = None,
    skip: int = 0,
    limit: int = 500,
    db: Session = Depends(get_db),
):
    query = db.query(BankTransaction)
    if category_id:
        query = query.filter(BankTransaction.category_id == category_id)
    if provider_invoice_id:
        query = query.filter(BankTransaction.provider_invoice_id == provider_invoice_id)
    return query.order_by(BankTransaction.booking_date.desc()).offset(skip).limit(limit).all()


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
def import_bank_xlsx(
    file: UploadFile,
    force_import_all: bool = False,
    db: Session = Depends(get_db),
):
    """Import bank transactions from an XLSX file.

    If duplicates are found, they are skipped by default and returned in
    ``potential_duplicates``. Pass ``force_import_all=true`` to re-import
    including duplicates.
    """
    validate_xlsx(file)

    # Save uploaded file with timestamped name for history
    imports_dir = settings.IMPORTS_DIR
    imports_dir.mkdir(parents=True, exist_ok=True)
    original_filename = file.filename or "bank_import.xlsx"
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    stored_name = f"bank_{ts}_{original_filename}"
    stored_path = imports_dir / stored_name

    with open(stored_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    result = import_bank_transactions(
        str(stored_path), db, force_import_all=force_import_all
    )

    # Record import history
    history = ImportHistory(
        file_type="bank",
        original_filename=original_filename,
        stored_path=f"imports/{stored_name}",
        record_count=result.imported,
        skipped_count=result.skipped_duplicate,
        notes="; ".join(result.errors) if result.errors else None,
    )
    db.add(history)
    db.commit()

    return BankImportResponse(
        imported=result.imported,
        skipped_duplicate=result.skipped_duplicate,
        auto_matched=result.auto_matched,
        invoice_auto_matched=result.invoice_auto_matched,
        invoice_suggested=result.invoice_suggested,
        potential_duplicates=[
            {"booking_date": d.booking_date, "amount_eur": d.amount_eur, "description": d.description}
            for d in result.potential_duplicates
        ],
        errors=result.errors,
    )


@router.post("/{tx_id}/match", response_model=MatchActionResponse)
def confirm_or_reject_match(
    tx_id: int,
    data: MatchAction,
    db: Session = Depends(get_db),
):
    """Confirm or reject a suggested transaction-to-invoice match."""
    tx = db.get(BankTransaction, tx_id)
    if not tx:
        raise HTTPException(404, f"Bank transaction {tx_id} not found")

    if data.action == "reject":
        reject_match(tx_id, db)
        return MatchActionResponse(
            success=True,
            message=f"Match for transaction {tx_id} rejected",
            match_status="rejected",
        )

    # Confirm: must have a suggested invoice to confirm
    if not tx.provider_invoice_id and tx.match_status != "suggested":
        raise HTTPException(400, "No suggested match to confirm for this transaction")

    # Find the suggested invoice — search for the best candidate
    from backend.services.transaction_matching import find_invoice_matches_for_transaction
    candidates = find_invoice_matches_for_transaction(tx, db)
    if not candidates:
        raise HTTPException(400, "No matching invoice found for this transaction")

    result = apply_match(tx_id, candidates[0].provider_invoice_id, db, "manual", data.bank_fee)
    return MatchActionResponse(
        success=True,
        message=f"Transaction {tx_id} matched to invoice",
        match_status=result["match_status"],
        amount_eur=result["amount_eur"],
        fx_rate=result["fx_rate"],
        bank_fee=result["bank_fee"],
    )


@router.post("/{tx_id}/manual-match", response_model=MatchActionResponse)
def manual_match(
    tx_id: int,
    data: ManualMatchRequest,
    db: Session = Depends(get_db),
):
    """Manually link a transaction to a specific provider invoice."""
    tx = db.get(BankTransaction, tx_id)
    if not tx:
        raise HTTPException(404, f"Bank transaction {tx_id} not found")

    from backend.models.provider_invoice import ProviderInvoice
    inv = db.get(ProviderInvoice, data.provider_invoice_id)
    if not inv:
        raise HTTPException(404, f"Provider invoice {data.provider_invoice_id} not found")

    result = apply_match(tx_id, data.provider_invoice_id, db, "manual", data.bank_fee)
    return MatchActionResponse(
        success=True,
        message=f"Transaction {tx_id} manually matched to invoice {inv.invoice_number}",
        match_status=result["match_status"],
        amount_eur=result["amount_eur"],
        fx_rate=result["fx_rate"],
        bank_fee=result["bank_fee"],
    )


@router.get("/import-history", response_model=list[ImportHistoryResponse])
def list_bank_import_history(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """List import history for bank transaction imports."""
    return (
        db.query(ImportHistory)
        .filter(ImportHistory.file_type == "bank")
        .order_by(ImportHistory.imported_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
