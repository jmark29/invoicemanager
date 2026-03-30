"""Cost calculation service — resolves line item amounts for each cost type.

Each line item on a generated invoice is resolved through one of four cost types:
- ``fixed``: constant amount from line_item_definitions.fixed_amount
- ``direct``: 1:1 pass-through of a provider invoice for the month
  - EUR providers: use provider_invoice.amount
  - USD providers: use bank_transaction.amount_eur (includes FX + fees)
- ``distributed``: multi-month provider invoice distributed by Hessen working days
  - Base = abs(bank_transaction.amount_eur) for the linked bank payment
  - Last month in the period receives the remainder
- ``upwork``: sum of Upwork transactions assigned to the month

The ``resolve_line_items`` function is the main orchestrator that resolves
all positions for a client/month, returning amounts and warnings.
"""

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import and_
from sqlalchemy.orm import Session

from backend.models.bank_transaction import BankTransaction
from backend.models.cost_category import CostCategory
from backend.models.line_item_definition import LineItemDefinition
from backend.models.provider_invoice import ProviderInvoice
from backend.models.upwork_transaction import UpworkTransaction
from backend.services.working_days import distribute_cost_by_working_days


@dataclass
class ContributingInvoice:
    """A provider invoice that contributes to a line item amount."""

    provider_invoice_id: int
    invoice_number: str
    amount_eur: float
    assigned_month: str | None = None
    is_from_different_month: bool = False


@dataclass
class ResolvedLineItem:
    """A single resolved line item with its computed amount and metadata."""

    position: int
    label: str
    amount: float
    source_type: str  # fixed, direct, distributed, upwork, manual
    category_id: str | None = None
    provider_invoice_id: int | None = None
    distribution_source_id: int | None = None
    distribution_months: list[str] | None = None
    upwork_tx_ids: list[str] | None = None
    warnings: list[str] = field(default_factory=list)
    contributing_invoices: list[ContributingInvoice] = field(default_factory=list)


@dataclass
class InvoicePreview:
    """Result of resolving all line items for a client/month."""

    client_id: str
    year: int
    month: int
    items: list[ResolvedLineItem]
    net_total: float = 0.0
    vat_amount: float = 0.0
    gross_total: float = 0.0
    warnings: list[str] = field(default_factory=list)


def calculate_fixed_amount(definition: LineItemDefinition) -> ResolvedLineItem:
    """Resolve a fixed-amount line item."""
    amount = definition.fixed_amount or 0.0
    warnings = []
    if definition.fixed_amount is None:
        warnings.append(f"Pos {definition.position}: fixed_amount is not set")
    return ResolvedLineItem(
        position=definition.position,
        label=definition.label,
        amount=amount,
        source_type="fixed",
        warnings=warnings,
    )


def calculate_direct_amount(
    definition: LineItemDefinition,
    year: int,
    month: int,
    db: Session,
) -> ResolvedLineItem:
    """Resolve a direct (1:1 pass-through) line item for the given month.

    For EUR providers, uses provider_invoice.amount.
    For USD providers, uses abs(bank_transaction.amount_eur) linked to the invoice.
    """
    month_str = f"{year}-{month:02d}"
    warnings: list[str] = []

    category = db.get(CostCategory, definition.category_id)
    if not category:
        return ResolvedLineItem(
            position=definition.position,
            label=definition.label,
            amount=0.0,
            source_type="direct",
            category_id=definition.category_id,
            warnings=[f"Pos {definition.position}: category '{definition.category_id}' not found"],
        )

    # Find provider invoice for this month (by assigned_month)
    invoice = (
        db.query(ProviderInvoice)
        .filter(
            and_(
                ProviderInvoice.category_id == definition.category_id,
                ProviderInvoice.assigned_month == month_str,
            )
        )
        .first()
    )

    if not invoice:
        return ResolvedLineItem(
            position=definition.position,
            label=definition.label,
            amount=0.0,
            source_type="direct",
            category_id=definition.category_id,
            warnings=[f"Pos {definition.position}: no provider invoice for {month_str}"],
        )

    # Prefer denormalized amount_eur (set by transaction matching) when available.
    # This includes FX conversion + banking fees for foreign currency invoices.
    if invoice.amount_eur is not None:
        amount = invoice.amount_eur
    elif category.currency == "USD":
        # Fallback: look up linked bank transaction directly
        bank_tx = (
            db.query(BankTransaction)
            .filter(BankTransaction.provider_invoice_id == invoice.id)
            .first()
        )
        if bank_tx:
            amount = abs(bank_tx.amount_eur)
        else:
            amount = 0.0
            warnings.append(
                f"Pos {definition.position}: USD invoice {invoice.invoice_number} "
                f"has no linked bank transaction"
            )
    else:
        amount = invoice.amount

    return ResolvedLineItem(
        position=definition.position,
        label=definition.label,
        amount=amount,
        source_type="direct",
        category_id=definition.category_id,
        provider_invoice_id=invoice.id,
        warnings=warnings,
    )


def calculate_distributed_amount(
    definition: LineItemDefinition,
    year: int,
    month: int,
    db: Session,
) -> ResolvedLineItem:
    """Resolve a distributed line item for the given month.

    Finds the multi-month provider invoice that covers this month,
    then distributes the bank payment amount across covered months
    proportional to Hessen working days. The last month gets the remainder.
    """
    month_str = f"{year}-{month:02d}"
    warnings: list[str] = []

    # Find the provider invoice whose covers_months includes this month
    invoices = (
        db.query(ProviderInvoice)
        .filter(ProviderInvoice.category_id == definition.category_id)
        .all()
    )

    target_invoice = None
    for inv in invoices:
        if month_str in inv.covers_months:
            target_invoice = inv
            break

    if not target_invoice:
        return ResolvedLineItem(
            position=definition.position,
            label=definition.label,
            amount=0.0,
            source_type="distributed",
            category_id=definition.category_id,
            warnings=[
                f"Pos {definition.position}: no provider invoice covers {month_str} "
                f"for category '{definition.category_id}'"
            ],
        )

    # Find the bank payment for this invoice
    bank_tx = (
        db.query(BankTransaction)
        .filter(BankTransaction.provider_invoice_id == target_invoice.id)
        .first()
    )

    if not bank_tx:
        return ResolvedLineItem(
            position=definition.position,
            label=definition.label,
            amount=0.0,
            source_type="distributed",
            category_id=definition.category_id,
            distribution_source_id=target_invoice.id,
            distribution_months=target_invoice.covers_months,
            warnings=[
                f"Pos {definition.position}: invoice {target_invoice.invoice_number} "
                f"has no linked bank transaction"
            ],
        )

    # Prefer denormalized amount_eur from invoice (includes bank fees),
    # fall back to bank transaction amount
    base_amount = target_invoice.amount_eur if target_invoice.amount_eur is not None else abs(bank_tx.amount_eur)
    months_tuples = []
    for m_str in target_invoice.covers_months:
        parts = m_str.split("-")
        months_tuples.append((int(parts[0]), int(parts[1])))

    distribution = distribute_cost_by_working_days(base_amount, months_tuples)
    this_month_amount = distribution.get((year, month), 0.0)

    return ResolvedLineItem(
        position=definition.position,
        label=definition.label,
        amount=this_month_amount,
        source_type="distributed",
        category_id=definition.category_id,
        distribution_source_id=target_invoice.id,
        distribution_months=target_invoice.covers_months,
        warnings=warnings,
    )


def calculate_upwork_amount(
    definition: LineItemDefinition,
    year: int,
    month: int,
    db: Session,
) -> ResolvedLineItem:
    """Resolve an Upwork line item by summing transactions assigned to this month."""
    month_str = f"{year}-{month:02d}"

    transactions = (
        db.query(UpworkTransaction)
        .filter(UpworkTransaction.assigned_month == month_str)
        .all()
    )

    total = Decimal("0.00")
    tx_ids = []
    for tx in transactions:
        total += Decimal(str(tx.amount_eur))
        tx_ids.append(tx.tx_id)

    amount = float(total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    warnings = []
    if not transactions:
        warnings.append(f"Pos {definition.position}: no Upwork transactions for {month_str}")

    return ResolvedLineItem(
        position=definition.position,
        label=definition.label,
        amount=amount,
        source_type="upwork",
        category_id=definition.category_id,
        upwork_tx_ids=tx_ids if tx_ids else None,
        warnings=warnings,
    )


def resolve_line_items(
    client_id: str,
    year: int,
    month: int,
    db: Session,
) -> InvoicePreview:
    """Resolve all line item amounts for a client/month and compute totals.

    Fetches the client's line item definitions, resolves each one through
    its cost type, then calculates net, VAT (19%), and gross totals.

    Returns an InvoicePreview with all resolved items and any warnings.
    """
    definitions = (
        db.query(LineItemDefinition)
        .filter(LineItemDefinition.client_id == client_id)
        .order_by(LineItemDefinition.sort_order, LineItemDefinition.position)
        .all()
    )

    items: list[ResolvedLineItem] = []
    all_warnings: list[str] = []

    for defn in definitions:
        if defn.source_type == "fixed":
            item = calculate_fixed_amount(defn)
        elif defn.source_type == "category":
            # Determine the cost type from the linked category
            category = db.get(CostCategory, defn.category_id)
            if not category:
                item = ResolvedLineItem(
                    position=defn.position,
                    label=defn.label,
                    amount=0.0,
                    source_type="unknown",
                    category_id=defn.category_id,
                    warnings=[f"Pos {defn.position}: category '{defn.category_id}' not found"],
                )
            elif category.cost_type == "direct":
                item = calculate_direct_amount(defn, year, month, db)
            elif category.cost_type == "distributed":
                item = calculate_distributed_amount(defn, year, month, db)
            elif category.cost_type == "upwork":
                item = calculate_upwork_amount(defn, year, month, db)
            else:
                item = ResolvedLineItem(
                    position=defn.position,
                    label=defn.label,
                    amount=0.0,
                    source_type=category.cost_type,
                    category_id=defn.category_id,
                    warnings=[
                        f"Pos {defn.position}: unsupported cost type '{category.cost_type}'"
                    ],
                )
        elif defn.source_type == "manual":
            # Manual items have no automatic resolution; amount = 0 until overridden
            item = ResolvedLineItem(
                position=defn.position,
                label=defn.label,
                amount=0.0,
                source_type="manual",
                category_id=defn.category_id,
            )
        else:
            item = ResolvedLineItem(
                position=defn.position,
                label=defn.label,
                amount=0.0,
                source_type=defn.source_type,
                warnings=[
                    f"Pos {defn.position}: unknown source_type '{defn.source_type}'"
                ],
            )

        items.append(item)
        all_warnings.extend(item.warnings)

    # Calculate totals using Decimal
    net = sum((Decimal(str(item.amount)) for item in items), Decimal("0"))
    net_rounded = net.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    vat = (net_rounded * Decimal("0.19")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    gross = net_rounded + vat

    return InvoicePreview(
        client_id=client_id,
        year=year,
        month=month,
        items=items,
        net_total=float(net_rounded),
        vat_amount=float(vat),
        gross_total=float(gross),
        warnings=all_warnings,
    )


# ── Running-Balance Resolution ───────────────────────────────────────


def _provider_cost_eur(inv: ProviderInvoice) -> float:
    """Get EUR cost for a provider invoice (amount_eur preferred, else amount)."""
    if inv.amount_eur is not None:
        return inv.amount_eur
    return inv.amount


def _get_effective_eur_amount(inv: ProviderInvoice, db: Session) -> float:
    """Get effective EUR amount for a provider invoice.

    Priority: amount_eur > bank transaction amount > invoice amount.
    Handles USD invoices by looking up linked bank transactions.
    """
    if inv.amount_eur is not None:
        return inv.amount_eur
    if inv.currency and inv.currency != "EUR":
        # Look up linked bank transaction for EUR amount
        bank_tx = (
            db.query(BankTransaction)
            .filter(BankTransaction.provider_invoice_id == inv.id)
            .first()
        )
        if bank_tx:
            return abs(bank_tx.amount_eur)
    return inv.amount


def _resolve_direct_running_balance(
    defn: LineItemDefinition,
    category: CostCategory,
    target_month_str: str,
    excluded: set[int],
    db: Session,
) -> ResolvedLineItem:
    """Resolve a direct cost using running-balance (un-invoiced provider costs)."""
    from backend.services.cost_reconciliation import get_uninvoiced_provider_costs

    uninvoiced = get_uninvoiced_provider_costs(defn.category_id, db)
    uninvoiced = [inv for inv in uninvoiced if inv.id not in excluded]

    total = Decimal("0")
    contributing: list[ContributingInvoice] = []
    for inv in uninvoiced:
        cost = _get_effective_eur_amount(inv, db)
        total += Decimal(str(cost))
        inv_month = inv.assigned_month or (
            f"{inv.invoice_date.year}-{inv.invoice_date.month:02d}"
            if inv.invoice_date else None
        )
        contributing.append(
            ContributingInvoice(
                provider_invoice_id=inv.id,
                invoice_number=inv.invoice_number,
                amount_eur=cost,
                assigned_month=inv_month,
                is_from_different_month=(inv_month != target_month_str if inv_month else False),
            )
        )

    amount = float(total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    warnings: list[str] = []
    if not uninvoiced:
        warnings.append(
            f"Pos {defn.position}: no un-invoiced provider costs for '{defn.category_id}'"
        )

    return ResolvedLineItem(
        position=defn.position,
        label=defn.label,
        amount=amount,
        source_type=category.cost_type,
        category_id=defn.category_id,
        warnings=warnings,
        contributing_invoices=contributing,
    )


def _resolve_distributed_running_balance(
    defn: LineItemDefinition,
    year: int,
    month: int,
    target_month_str: str,
    excluded: set[int],
    db: Session,
) -> ResolvedLineItem:
    """Resolve a distributed cost using running-balance.

    Still computes per-month distribution by working days, but checks
    each month's portion against InvoiceLineItemSource to determine
    if it's already been invoiced. Sums un-invoiced portions.
    """
    from backend.models.invoice_line_item_source import InvoiceLineItemSource

    # Find all provider invoices for this category
    invoices = (
        db.query(ProviderInvoice)
        .filter(ProviderInvoice.category_id == defn.category_id)
        .all()
    )

    # Get all linked provider invoice IDs
    pi_ids = [inv.id for inv in invoices]
    linked_ids = set()
    if pi_ids:
        linked_ids = {
            row[0]
            for row in db.query(InvoiceLineItemSource.provider_invoice_id)
            .filter(InvoiceLineItemSource.provider_invoice_id.in_(pi_ids))
            .distinct()
            .all()
        }

    total = Decimal("0")
    contributing: list[ContributingInvoice] = []
    warnings: list[str] = []

    for inv in invoices:
        if inv.id in excluded or inv.id in linked_ids:
            continue

        # Get base amount (prefer amount_eur, fallback to bank tx)
        base_amount = _get_effective_eur_amount(inv, db)

        if inv.covers_months and len(inv.covers_months) > 1:
            # For distributed invoices, use bank payment amount as base
            # (matches original per-month behavior)
            bank_tx = (
                db.query(BankTransaction)
                .filter(BankTransaction.provider_invoice_id == inv.id)
                .first()
            )
            if bank_tx:
                base_amount = inv.amount_eur if inv.amount_eur is not None else abs(bank_tx.amount_eur)

            # Distribute across covered months
            months_tuples = []
            for m_str in inv.covers_months:
                parts = m_str.split("-")
                months_tuples.append((int(parts[0]), int(parts[1])))

            distribution = distribute_cost_by_working_days(base_amount, months_tuples)

            # Sum the un-invoiced portions
            for (y, m), month_amount in distribution.items():
                total += Decimal(str(month_amount))

            contributing.append(
                ContributingInvoice(
                    provider_invoice_id=inv.id,
                    invoice_number=inv.invoice_number,
                    amount_eur=base_amount,
                    assigned_month=inv.assigned_month,
                    is_from_different_month=True,
                )
            )
        else:
            # Single-month distributed invoice
            total += Decimal(str(base_amount))
            inv_month = inv.assigned_month or (
                f"{inv.invoice_date.year}-{inv.invoice_date.month:02d}"
                if inv.invoice_date else None
            )
            contributing.append(
                ContributingInvoice(
                    provider_invoice_id=inv.id,
                    invoice_number=inv.invoice_number,
                    amount_eur=base_amount,
                    assigned_month=inv_month,
                    is_from_different_month=(inv_month != target_month_str if inv_month else False),
                )
            )

    amount = float(total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    if not contributing:
        warnings.append(
            f"Pos {defn.position}: no un-invoiced provider costs for '{defn.category_id}'"
        )

    return ResolvedLineItem(
        position=defn.position,
        label=defn.label,
        amount=amount,
        source_type="distributed",
        category_id=defn.category_id,
        warnings=warnings,
        contributing_invoices=contributing,
    )


def resolve_line_items_running_balance(
    client_id: str,
    year: int,
    month: int,
    db: Session,
    excluded_provider_invoice_ids: list[int] | None = None,
) -> InvoicePreview:
    """Resolve line items using the running-balance approach.

    For category-based items, uses un-invoiced provider costs (across all months)
    instead of per-month costs. Fixed items use configured amounts.
    Manual items return 0.

    Args:
        excluded_provider_invoice_ids: Provider invoices the user chose to defer.
    """
    from backend.services.cost_reconciliation import get_uninvoiced_provider_costs

    excluded = set(excluded_provider_invoice_ids or [])
    target_month_str = f"{year}-{month:02d}"

    definitions = (
        db.query(LineItemDefinition)
        .filter(LineItemDefinition.client_id == client_id)
        .order_by(LineItemDefinition.sort_order, LineItemDefinition.position)
        .all()
    )

    items: list[ResolvedLineItem] = []
    all_warnings: list[str] = []

    for defn in definitions:
        if defn.source_type == "fixed":
            item = calculate_fixed_amount(defn)

        elif defn.source_type == "category":
            category = db.get(CostCategory, defn.category_id)
            if not category:
                item = ResolvedLineItem(
                    position=defn.position,
                    label=defn.label,
                    amount=0.0,
                    source_type="unknown",
                    category_id=defn.category_id,
                    warnings=[f"Pos {defn.position}: category '{defn.category_id}' not found"],
                )
            elif category.cost_type == "upwork":
                # Upwork: find unassigned transactions (not yet linked to an invoice)
                txs = (
                    db.query(UpworkTransaction)
                    .filter(UpworkTransaction.assigned_invoice_id.is_(None))
                    .all()
                )
                total = Decimal("0")
                tx_ids = []
                for tx in txs:
                    total += Decimal(str(tx.amount_eur))
                    tx_ids.append(tx.tx_id)

                amount = float(total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
                warnings = []
                if not txs:
                    warnings.append(f"Pos {defn.position}: no un-invoiced Upwork transactions")

                item = ResolvedLineItem(
                    position=defn.position,
                    label=defn.label,
                    amount=amount,
                    source_type="upwork",
                    category_id=defn.category_id,
                    upwork_tx_ids=tx_ids if tx_ids else None,
                    warnings=warnings,
                )
            elif category.cost_type == "distributed":
                # Distributed: compute per-month distribution, include un-invoiced portions
                item = _resolve_distributed_running_balance(
                    defn, year, month, target_month_str, excluded, db
                )
            else:
                # direct: use un-invoiced provider costs
                item = _resolve_direct_running_balance(
                    defn, category, target_month_str, excluded, db
                )

        elif defn.source_type == "manual":
            item = ResolvedLineItem(
                position=defn.position,
                label=defn.label,
                amount=0.0,
                source_type="manual",
                category_id=defn.category_id,
            )
        else:
            item = ResolvedLineItem(
                position=defn.position,
                label=defn.label,
                amount=0.0,
                source_type=defn.source_type,
                warnings=[f"Pos {defn.position}: unknown source_type '{defn.source_type}'"],
            )

        items.append(item)
        all_warnings.extend(item.warnings)

    # Calculate totals using Decimal
    net = sum((Decimal(str(item.amount)) for item in items), Decimal("0"))
    net_rounded = net.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    vat = (net_rounded * Decimal("0.19")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    gross = net_rounded + vat

    return InvoicePreview(
        client_id=client_id,
        year=year,
        month=month,
        items=items,
        net_total=float(net_rounded),
        vat_amount=float(vat),
        gross_total=float(gross),
        warnings=all_warnings,
    )
