"""Cost reconciliation service — running balance per cost category.

Tracks whether every provider cost has been invoiced to the client:
  Running Balance = Total provider costs (EUR) − Total invoiced for that category

A positive balance means under-invoiced costs remain.
A zero balance means fully reconciled.
A negative balance means over-invoiced.
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.models.cost_category import CostCategory
from backend.models.generated_invoice import GeneratedInvoiceItem
from backend.models.invoice_line_item_source import InvoiceLineItemSource
from backend.models.provider_invoice import ProviderInvoice


@dataclass
class CategoryBalance:
    category_id: str
    category_name: str
    total_provider_costs: float
    total_invoiced: float
    delta: float
    status: str  # balanced, under_invoiced, over_invoiced


@dataclass
class ProviderInvoiceStatus:
    id: int
    invoice_number: str
    invoice_date: date | None
    amount_eur: float
    assigned_month: str | None
    linked_invoice_number: str | None = None
    linked_line_item_id: int | None = None
    amount_invoiced: float | None = None
    status: str = "unlinked"  # linked, unlinked, amount_mismatch


@dataclass
class CategoryReconciliationDetail:
    category_id: str
    category_name: str
    balance: CategoryBalance
    provider_invoices: list[ProviderInvoiceStatus] = field(default_factory=list)


@dataclass
class CostReconciliationSummary:
    categories: list[CategoryBalance]
    total_provider_costs: float = 0.0
    total_invoiced: float = 0.0
    total_delta: float = 0.0
    balanced_count: int = 0
    open_count: int = 0


def _provider_cost_eur(inv: ProviderInvoice) -> float:
    """Get the EUR cost for a provider invoice (amount_eur preferred, else amount)."""
    if inv.amount_eur is not None:
        return inv.amount_eur
    return inv.amount


def get_cost_reconciliation_summary(db: Session) -> CostReconciliationSummary:
    """Compute running balance for all active cost categories with provider invoices."""
    categories = (
        db.query(CostCategory)
        .filter(CostCategory.active.is_(True))
        .order_by(CostCategory.sort_order)
        .all()
    )

    # Get all linked provider invoice IDs with their contributed amounts
    linked_data = (
        db.query(
            InvoiceLineItemSource.provider_invoice_id,
            func.sum(InvoiceLineItemSource.amount_contributed),
        )
        .group_by(InvoiceLineItemSource.provider_invoice_id)
        .all()
    )
    linked_amounts: dict[int, float] = {
        row[0]: float(row[1]) if row[1] else 0.0 for row in linked_data
    }

    balances: list[CategoryBalance] = []

    for cat in categories:
        if cat.cost_type == "fixed":
            continue  # Fixed costs don't have provider invoices

        # Sum all provider costs for this category
        provider_invoices = (
            db.query(ProviderInvoice)
            .filter(ProviderInvoice.category_id == cat.id)
            .all()
        )

        if not provider_invoices:
            continue

        total_costs = Decimal("0")
        total_invoiced = Decimal("0")

        for inv in provider_invoices:
            cost = Decimal(str(_provider_cost_eur(inv)))
            total_costs += cost
            if inv.id in linked_amounts:
                total_invoiced += Decimal(str(linked_amounts[inv.id]))

        total_costs = total_costs.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        total_invoiced = total_invoiced.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        delta = (total_costs - total_invoiced).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        if delta == 0:
            status = "balanced"
        elif delta > 0:
            status = "under_invoiced"
        else:
            status = "over_invoiced"

        balances.append(
            CategoryBalance(
                category_id=cat.id,
                category_name=cat.name,
                total_provider_costs=float(total_costs),
                total_invoiced=float(total_invoiced),
                delta=float(delta),
                status=status,
            )
        )

    summary_costs = sum(b.total_provider_costs for b in balances)
    summary_invoiced = sum(b.total_invoiced for b in balances)
    summary_delta = sum(b.delta for b in balances)

    return CostReconciliationSummary(
        categories=balances,
        total_provider_costs=summary_costs,
        total_invoiced=summary_invoiced,
        total_delta=summary_delta,
        balanced_count=sum(1 for b in balances if b.status == "balanced"),
        open_count=sum(1 for b in balances if b.status != "balanced"),
    )


def get_category_reconciliation_detail(
    category_id: str, db: Session
) -> CategoryReconciliationDetail:
    """Get detailed provider invoice linkage for a single category."""
    cat = db.get(CostCategory, category_id)
    if not cat:
        raise ValueError(f"Category '{category_id}' not found")

    provider_invoices = (
        db.query(ProviderInvoice)
        .filter(ProviderInvoice.category_id == category_id)
        .order_by(ProviderInvoice.invoice_date)
        .all()
    )

    # Get all source links for provider invoices in this category
    pi_ids = [inv.id for inv in provider_invoices]
    source_links = (
        db.query(InvoiceLineItemSource)
        .filter(InvoiceLineItemSource.provider_invoice_id.in_(pi_ids))
        .all()
    ) if pi_ids else []

    # Build lookup: provider_invoice_id → list of source links
    links_by_pi: dict[int, list[InvoiceLineItemSource]] = {}
    for link in source_links:
        links_by_pi.setdefault(link.provider_invoice_id, []).append(link)

    # Get invoice numbers for linked line items
    line_item_ids = [link.line_item_id for link in source_links]
    line_items = (
        db.query(GeneratedInvoiceItem)
        .filter(GeneratedInvoiceItem.id.in_(line_item_ids))
        .all()
    ) if line_item_ids else []

    # Build lookup: line_item_id → (invoice_number, invoice)
    from backend.models.generated_invoice import GeneratedInvoice

    li_to_invoice: dict[int, tuple[str, int]] = {}
    for li in line_items:
        invoice = db.get(GeneratedInvoice, li.invoice_id)
        if invoice:
            li_to_invoice[li.id] = (invoice.invoice_number, li.position)

    total_costs = Decimal("0")
    total_invoiced = Decimal("0")
    statuses: list[ProviderInvoiceStatus] = []

    for inv in provider_invoices:
        cost = _provider_cost_eur(inv)
        total_costs += Decimal(str(cost))

        links = links_by_pi.get(inv.id, [])
        if links:
            # Sum all contributions for this provider invoice
            contributed = sum(l.amount_contributed or 0 for l in links)
            total_invoiced += Decimal(str(contributed))

            # Get the first linked invoice info for display
            first_link = links[0]
            inv_info = li_to_invoice.get(first_link.line_item_id)
            linked_inv_num = None
            if inv_info:
                linked_inv_num = f"AR{inv_info[0]}, Pos {inv_info[1]}"

            # Check if amounts match
            cost_dec = Decimal(str(cost)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            contrib_dec = Decimal(str(contributed)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if cost_dec == contrib_dec:
                link_status = "linked"
            else:
                link_status = "amount_mismatch"

            statuses.append(
                ProviderInvoiceStatus(
                    id=inv.id,
                    invoice_number=inv.invoice_number,
                    invoice_date=inv.invoice_date,
                    amount_eur=cost,
                    assigned_month=inv.assigned_month,
                    linked_invoice_number=linked_inv_num,
                    linked_line_item_id=first_link.line_item_id,
                    amount_invoiced=contributed,
                    status=link_status,
                )
            )
        else:
            statuses.append(
                ProviderInvoiceStatus(
                    id=inv.id,
                    invoice_number=inv.invoice_number,
                    invoice_date=inv.invoice_date,
                    amount_eur=cost,
                    assigned_month=inv.assigned_month,
                    status="unlinked",
                )
            )

    total_costs_f = float(total_costs.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    total_invoiced_f = float(total_invoiced.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    delta = total_costs_f - total_invoiced_f

    if abs(delta) < 0.01:
        balance_status = "balanced"
    elif delta > 0:
        balance_status = "under_invoiced"
    else:
        balance_status = "over_invoiced"

    balance = CategoryBalance(
        category_id=cat.id,
        category_name=cat.name,
        total_provider_costs=total_costs_f,
        total_invoiced=total_invoiced_f,
        delta=round(delta, 2),
        status=balance_status,
    )

    return CategoryReconciliationDetail(
        category_id=cat.id,
        category_name=cat.name,
        balance=balance,
        provider_invoices=statuses,
    )


def get_uninvoiced_provider_costs(
    category_id: str, db: Session
) -> list[ProviderInvoice]:
    """Return provider invoices for a category that have no source links."""
    all_invoices = (
        db.query(ProviderInvoice)
        .filter(ProviderInvoice.category_id == category_id)
        .all()
    )

    if not all_invoices:
        return []

    pi_ids = [inv.id for inv in all_invoices]
    linked_ids = set(
        row[0]
        for row in db.query(InvoiceLineItemSource.provider_invoice_id)
        .filter(InvoiceLineItemSource.provider_invoice_id.in_(pi_ids))
        .distinct()
        .all()
    )

    return [inv for inv in all_invoices if inv.id not in linked_ids]
