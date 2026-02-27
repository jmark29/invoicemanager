"""Reconciliation service — compare provider invoices vs bank payments for a month."""

from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import and_
from sqlalchemy.orm import Session

from backend.models.bank_transaction import BankTransaction
from backend.models.cost_category import CostCategory
from backend.models.generated_invoice import GeneratedInvoice
from backend.models.payment_receipt import PaymentReceipt
from backend.models.provider_invoice import ProviderInvoice


@dataclass
class ProviderInvoiceMatch:
    category_id: str
    category_name: str
    invoice_number: str
    invoice_amount: float
    has_bank_payment: bool
    bank_amount: float | None = None
    bank_booking_date: date | None = None


@dataclass
class UnmatchedBankTransaction:
    id: int
    booking_date: date
    amount_eur: float
    description: str
    category_id: str | None = None


@dataclass
class InvoicePaymentStatus:
    invoice_number: str
    status: str
    gross_total: float
    total_paid: float
    balance: float


@dataclass
class MonthlyReconciliation:
    year: int
    month: int
    provider_matches: list[ProviderInvoiceMatch] = field(default_factory=list)
    matched_count: int = 0
    unmatched_count: int = 0
    unmatched_bank_transactions: list[UnmatchedBankTransaction] = field(
        default_factory=list
    )
    invoice_status: InvoicePaymentStatus | None = None


def reconcile_month(year: int, month: int, db: Session) -> MonthlyReconciliation:
    """Reconcile provider invoices vs bank payments for a specific month.

    Returns structured data comparing:
    - Provider invoices to their linked bank payments
    - Unmatched bank transactions
    - Generated invoice payment status
    """
    month_str = f"{year}-{month:02d}"
    result = MonthlyReconciliation(year=year, month=month)

    # Provider invoices vs bank payments per category
    categories = (
        db.query(CostCategory)
        .filter(CostCategory.active.is_(True))
        .order_by(CostCategory.sort_order)
        .all()
    )

    for cat in categories:
        invoices = (
            db.query(ProviderInvoice)
            .filter(
                ProviderInvoice.category_id == cat.id,
                ProviderInvoice.assigned_month == month_str,
            )
            .all()
        )

        for inv in invoices:
            bank_tx = (
                db.query(BankTransaction)
                .filter(BankTransaction.provider_invoice_id == inv.id)
                .first()
            )

            match = ProviderInvoiceMatch(
                category_id=cat.id,
                category_name=cat.name,
                invoice_number=inv.invoice_number,
                invoice_amount=inv.amount,
                has_bank_payment=bank_tx is not None,
                bank_amount=abs(bank_tx.amount_eur) if bank_tx else None,
                bank_booking_date=bank_tx.booking_date if bank_tx else None,
            )
            result.provider_matches.append(match)

            if bank_tx:
                result.matched_count += 1
            else:
                result.unmatched_count += 1

    # Unmatched bank transactions for this month
    unmatched_bank = (
        db.query(BankTransaction)
        .filter(
            BankTransaction.provider_invoice_id.is_(None),
            BankTransaction.category_id.isnot(None),
        )
        .all()
    )
    for tx in unmatched_bank:
        if tx.booking_date.year == year and tx.booking_date.month == month:
            result.unmatched_bank_transactions.append(
                UnmatchedBankTransaction(
                    id=tx.id,
                    booking_date=tx.booking_date,
                    amount_eur=abs(tx.amount_eur),
                    description=tx.description or "",
                    category_id=tx.category_id,
                )
            )

    # Generated invoice + payment status
    gen_inv = (
        db.query(GeneratedInvoice)
        .filter(
            and_(
                GeneratedInvoice.period_year == year,
                GeneratedInvoice.period_month == month,
            )
        )
        .first()
    )

    if gen_inv:
        payments = (
            db.query(PaymentReceipt)
            .filter(PaymentReceipt.matched_invoice_id == gen_inv.id)
            .all()
        )
        total_paid = sum(p.amount_eur for p in payments)
        result.invoice_status = InvoicePaymentStatus(
            invoice_number=gen_inv.invoice_number,
            status=gen_inv.status,
            gross_total=gen_inv.gross_total,
            total_paid=total_paid,
            balance=gen_inv.gross_total - total_paid,
        )

    return result
