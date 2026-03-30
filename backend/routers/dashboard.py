"""Dashboard aggregation, reconciliation, and cost reconciliation endpoints."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, extract, func, or_
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.bank_transaction import BankTransaction
from backend.models.generated_invoice import GeneratedInvoice, GeneratedInvoiceItem
from backend.models.payment_receipt import PaymentReceipt
from backend.models.provider_invoice import ProviderInvoice
from backend.schemas.cost_reconciliation import (
    CategoryBalanceResponse,
    CategoryReconciliationDetailResponse,
    CostReconciliationSummaryResponse,
    MissingMonthResponse,
    MissingMonthsResponse,
    ProviderInvoiceStatusResponse,
)
from backend.schemas.dashboard import (
    CompletedMatchResponse,
    InvoicePaymentStatusResponse,
    MonthlyDashboardResponse,
    OpenInvoicesResponse,
    ProviderInvoiceMatchResponse,
    ReconciliationResponse,
    SuggestedMatchResponse,
    UnmatchedBankTransactionResponse,
    UnmatchedInvoiceResponse,
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
    month_str = f"{year}-{month:02d}"

    # Suggested matches: bank transactions with match_status='suggested'
    suggested_txns = db.query(BankTransaction).filter(
        BankTransaction.match_status == "suggested",
        BankTransaction.provider_invoice_id.is_(None),
        extract('year', BankTransaction.booking_date) == year,
        extract('month', BankTransaction.booking_date) == month,
    ).all()
    suggested_matches = []
    for tx in suggested_txns:
        # Find the best candidate invoice
        from backend.services.transaction_matching import find_invoice_matches_for_transaction
        candidates = find_invoice_matches_for_transaction(tx, db)
        if candidates:
            best = candidates[0]
            inv = db.get(ProviderInvoice, best.provider_invoice_id)
            if inv:
                suggested_matches.append(SuggestedMatchResponse(
                    bank_transaction_id=tx.id,
                    provider_invoice_id=inv.id,
                    confidence=best.confidence,
                    match_reason=best.match_reason,
                    tx_booking_date=tx.booking_date,
                    tx_amount_eur=abs(tx.amount_eur),
                    tx_description=tx.description,
                    tx_category_id=tx.category_id,
                    inv_invoice_number=inv.invoice_number,
                    inv_amount=inv.amount,
                    inv_currency=inv.currency,
                    inv_category_id=inv.category_id,
                ))

    # Completed matches: linked pairs for this month
    completed_matches = []
    matched_invoices = db.query(ProviderInvoice).filter(
        ProviderInvoice.payment_status == "matched",
        or_(
            ProviderInvoice.assigned_month == month_str,
            and_(
                ProviderInvoice.assigned_month.is_(None),
                extract('year', ProviderInvoice.invoice_date) == year,
                extract('month', ProviderInvoice.invoice_date) == month,
            ),
        ),
    ).all()
    for inv in matched_invoices:
        tx = db.query(BankTransaction).filter(
            BankTransaction.provider_invoice_id == inv.id,
        ).first()
        if tx:
            completed_matches.append(CompletedMatchResponse(
                bank_transaction_id=tx.id,
                provider_invoice_id=inv.id,
                match_status=tx.match_status,
                tx_booking_date=tx.booking_date,
                tx_amount_eur=abs(tx.amount_eur),
                tx_description=tx.description,
                inv_invoice_number=inv.invoice_number,
                inv_amount=inv.amount,
                inv_currency=inv.currency,
                inv_category_id=inv.category_id,
                amount_eur=inv.amount_eur,
                fx_rate=inv.fx_rate,
                bank_fee=inv.bank_fee,
            ))

    # Unmatched invoices for this month
    unmatched_invs = db.query(ProviderInvoice).filter(
        ProviderInvoice.payment_status.in_(["unpaid", "partial"]),
        or_(
            ProviderInvoice.assigned_month == month_str,
            and_(
                ProviderInvoice.assigned_month.is_(None),
                extract('year', ProviderInvoice.invoice_date) == year,
                extract('month', ProviderInvoice.invoice_date) == month,
            ),
        ),
    ).all()
    unmatched_invoices = [
        UnmatchedInvoiceResponse(
            id=inv.id,
            invoice_number=inv.invoice_number,
            invoice_date=inv.invoice_date,
            amount=inv.amount,
            currency=inv.currency,
            category_id=inv.category_id,
            assigned_month=inv.assigned_month,
        )
        for inv in unmatched_invs
    ]

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
        suggested_matches=suggested_matches,
        completed_matches=completed_matches,
        unmatched_invoices=unmatched_invoices,
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


# ── Cost Reconciliation (Running Balance) ────────────────────────────


@router.get(
    "/cost-reconciliation",
    response_model=CostReconciliationSummaryResponse,
)
def get_cost_reconciliation(db: Session = Depends(get_db)):
    """Get running balance summary across all active cost categories."""
    from backend.services.cost_reconciliation import get_cost_reconciliation_summary

    summary = get_cost_reconciliation_summary(db)
    return CostReconciliationSummaryResponse(
        categories=[
            CategoryBalanceResponse(
                category_id=b.category_id,
                category_name=b.category_name,
                total_provider_costs=b.total_provider_costs,
                total_invoiced=b.total_invoiced,
                delta=b.delta,
                status=b.status,
            )
            for b in summary.categories
        ],
        total_provider_costs=summary.total_provider_costs,
        total_invoiced=summary.total_invoiced,
        total_delta=summary.total_delta,
        balanced_count=summary.balanced_count,
        open_count=summary.open_count,
    )


@router.get(
    "/cost-reconciliation/{category_id}",
    response_model=CategoryReconciliationDetailResponse,
)
def get_category_reconciliation(category_id: str, db: Session = Depends(get_db)):
    """Get detailed provider invoice linkage status for a single category."""
    from backend.services.cost_reconciliation import get_category_reconciliation_detail

    try:
        detail = get_category_reconciliation_detail(category_id, db)
    except ValueError as e:
        raise HTTPException(404, str(e))

    return CategoryReconciliationDetailResponse(
        category_id=detail.category_id,
        category_name=detail.category_name,
        balance=CategoryBalanceResponse(
            category_id=detail.balance.category_id,
            category_name=detail.balance.category_name,
            total_provider_costs=detail.balance.total_provider_costs,
            total_invoiced=detail.balance.total_invoiced,
            delta=detail.balance.delta,
            status=detail.balance.status,
        ),
        provider_invoices=[
            ProviderInvoiceStatusResponse(
                id=pi.id,
                invoice_number=pi.invoice_number,
                invoice_date=pi.invoice_date,
                amount_eur=pi.amount_eur,
                assigned_month=pi.assigned_month,
                linked_invoice_number=pi.linked_invoice_number,
                linked_line_item_id=pi.linked_line_item_id,
                amount_invoiced=pi.amount_invoiced,
                status=pi.status,
            )
            for pi in detail.provider_invoices
        ],
    )


# ── Missing Months ───────────────────────────────────────────────────

_MONTH_NAMES = [
    "", "Jan", "Feb", "Mär", "Apr", "Mai", "Jun",
    "Jul", "Aug", "Sep", "Okt", "Nov", "Dez",
]


@router.get("/missing-months", response_model=MissingMonthsResponse)
def get_missing_months(
    client_id: str | None = None,
    db: Session = Depends(get_db),
):
    """Determine which months are missing invoices.

    Scans from the earliest provider invoice month to the current month,
    checks which months have a GeneratedInvoice record.
    """
    # Find earliest provider invoice date
    earliest = db.query(func.min(ProviderInvoice.invoice_date)).scalar()
    if not earliest:
        return MissingMonthsResponse(months=[], total=0)

    start_year, start_month = earliest.year, earliest.month

    # Find current date
    today = date.today()
    end_year, end_month = today.year, today.month

    # Get all existing invoice months
    query = db.query(
        GeneratedInvoice.period_year,
        GeneratedInvoice.period_month,
    )
    if client_id:
        query = query.filter(GeneratedInvoice.client_id == client_id)
    existing = {(row[0], row[1]) for row in query.all()}

    # Build missing months list
    missing: list[MissingMonthResponse] = []
    y, m = start_year, start_month
    while (y, m) <= (end_year, end_month):
        if (y, m) not in existing:
            missing.append(
                MissingMonthResponse(
                    year=y,
                    month=m,
                    label=f"{_MONTH_NAMES[m]} {y}",
                )
            )
        m += 1
        if m > 12:
            m = 1
            y += 1

    return MissingMonthsResponse(months=missing, total=len(missing))
