"""CRUD endpoints for payment receipts."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.payment_receipt import PaymentReceipt
from backend.schemas.payment_receipt import (
    PaymentReceiptCreate,
    PaymentReceiptResponse,
    PaymentReceiptUpdate,
)

router = APIRouter(prefix="/api/payments", tags=["payments"])


@router.get("", response_model=list[PaymentReceiptResponse])
def list_payments(
    client_id: str | None = None,
    matched_invoice_id: int | None = None,
    skip: int = 0,
    limit: int = 500,
    db: Session = Depends(get_db),
):
    query = db.query(PaymentReceipt)
    if client_id:
        query = query.filter(PaymentReceipt.client_id == client_id)
    if matched_invoice_id:
        query = query.filter(PaymentReceipt.matched_invoice_id == matched_invoice_id)
    return query.order_by(PaymentReceipt.payment_date.desc()).offset(skip).limit(limit).all()


@router.get("/{payment_id}", response_model=PaymentReceiptResponse)
def get_payment(payment_id: int, db: Session = Depends(get_db)):
    payment = db.get(PaymentReceipt, payment_id)
    if not payment:
        raise HTTPException(404, f"Payment {payment_id} not found")
    return payment


@router.post("", response_model=PaymentReceiptResponse, status_code=201)
def create_payment(data: PaymentReceiptCreate, db: Session = Depends(get_db)):
    payment = PaymentReceipt(**data.model_dump())
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


@router.patch("/{payment_id}", response_model=PaymentReceiptResponse)
def update_payment(
    payment_id: int, data: PaymentReceiptUpdate, db: Session = Depends(get_db)
):
    payment = db.get(PaymentReceipt, payment_id)
    if not payment:
        raise HTTPException(404, f"Payment {payment_id} not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(payment, key, value)
    db.commit()
    db.refresh(payment)
    return payment


@router.delete("/{payment_id}", status_code=204)
def delete_payment(payment_id: int, db: Session = Depends(get_db)):
    payment = db.get(PaymentReceipt, payment_id)
    if not payment:
        raise HTTPException(404, f"Payment {payment_id} not found")
    db.delete(payment)
    db.commit()
