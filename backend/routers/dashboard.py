"""Dashboard aggregation and reconciliation endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.generated_invoice import GeneratedInvoice, GeneratedInvoiceItem
from backend.models.payment_receipt import PaymentReceipt
from backend.schemas.dashboard import (
    InvoicePaymentStatusResponse,
    MonthlyDashboardResponse,
    OpenInvoicesResponse,
    ProviderInvoiceMatchResponse,
    ReconciliationResponse,
    UnmatchedBankTransactionResponse,
)
from backend.schemas.generated_invoice import (
    GeneratedInvoiceItemResponse,
    GeneratedInvoiceListResponse,
)
from backend.services.reconciliation import reconcile_month

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/monthly/{year}/{month}", response_model=MonthlyDashboardResponse)
def get_monthly_dashboard(year: int, month: int, db: Session = Depends(get_db)):
    """Get summary data for a specific billing month."""
    inv = (
        db.query(GeneratedInvoice)
        .filter(
            GeneratedInvoice.period_year == year,
            GeneratedInvoice.period_month == month,
        )
        .first()
    )

    if not inv:
        return MonthlyDashboardResponse(year=year, month=month, has_invoice=False)

    items = (
        db.query(GeneratedInvoiceItem)
        .filter(GeneratedInvoiceItem.invoice_id == inv.id)
        .order_by(GeneratedInvoiceItem.position)
        .all()
    )

    payments = (
        db.query(PaymentReceipt)
        .filter(PaymentReceipt.matched_invoice_id == inv.id)
        .all()
    )
    payment_total = sum(p.amount_eur for p in payments)

    return MonthlyDashboardResponse(
        year=year,
        month=month,
        has_invoice=True,
        invoice=GeneratedInvoiceListResponse.model_validate(inv),
        items=[GeneratedInvoiceItemResponse.model_validate(i) for i in items],
        net_total=inv.net_total,
        vat_amount=inv.vat_amount,
        gross_total=inv.gross_total,
        payment_total=payment_total,
        payment_balance=inv.gross_total - payment_total,
    )


@router.get("/open-invoices", response_model=OpenInvoicesResponse)
def get_open_invoices(db: Session = Depends(get_db)):
    """Get all unpaid invoices (status != 'paid')."""
    invoices = (
        db.query(GeneratedInvoice)
        .filter(GeneratedInvoice.status != "paid")
        .order_by(
            GeneratedInvoice.period_year.desc(),
            GeneratedInvoice.period_month.desc(),
        )
        .all()
    )

    return OpenInvoicesResponse(
        invoices=[GeneratedInvoiceListResponse.model_validate(i) for i in invoices],
        count=len(invoices),
        total_gross=sum(i.gross_total for i in invoices),
        total_net=sum(i.net_total for i in invoices),
    )


@router.get("/reconciliation/{year}/{month}", response_model=ReconciliationResponse)
def get_reconciliation(year: int, month: int, db: Session = Depends(get_db)):
    """Get structured reconciliation data for a billing month."""
    recon = reconcile_month(year, month, db)

    return ReconciliationResponse(
        year=recon.year,
        month=recon.month,
        provider_matches=[
            ProviderInvoiceMatchResponse(
                category_id=m.category_id,
                category_name=m.category_name,
                invoice_number=m.invoice_number,
                invoice_amount=m.invoice_amount,
                has_bank_payment=m.has_bank_payment,
                bank_amount=m.bank_amount,
                bank_booking_date=m.bank_booking_date,
            )
            for m in recon.provider_matches
        ],
        matched_count=recon.matched_count,
        unmatched_count=recon.unmatched_count,
        unmatched_bank_transactions=[
            UnmatchedBankTransactionResponse(
                id=t.id,
                booking_date=t.booking_date,
                amount_eur=t.amount_eur,
                description=t.description,
                category_id=t.category_id,
            )
            for t in recon.unmatched_bank_transactions
        ],
        invoice_status=(
            InvoicePaymentStatusResponse(
                invoice_number=recon.invoice_status.invoice_number,
                status=recon.invoice_status.status,
                gross_total=recon.invoice_status.gross_total,
                total_paid=recon.invoice_status.total_paid,
                balance=recon.invoice_status.balance,
            )
            if recon.invoice_status
            else None
        ),
    )
