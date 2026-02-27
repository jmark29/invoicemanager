"""Read-only query tools for the Invoice Manager MCP server."""

from sqlalchemy import and_

from backend.models.bank_transaction import BankTransaction
from backend.models.cost_category import CostCategory
from backend.models.generated_invoice import GeneratedInvoice, GeneratedInvoiceItem
from backend.models.line_item_definition import LineItemDefinition
from backend.models.payment_receipt import PaymentReceipt
from backend.models.provider_invoice import ProviderInvoice
from backend.models.upwork_transaction import UpworkTransaction
from backend.services.cost_calculation import InvoicePreview
from backend.services.formatting import format_date_german, format_eur, format_month_year
from backend.services.invoice_engine import preview_invoice
from backend.services.reconciliation import reconcile_month
from backend.services.working_days import (
    distribute_cost_by_working_days,
    working_days_in_month,
)
from mcp_server.db import get_session
from mcp_server.server import mcp


def _parse_month(month: str) -> tuple[int, int]:
    """Parse 'YYYY-MM' into (year, month). Raises ValueError on bad format."""
    parts = month.strip().split("-")
    if len(parts) != 2:
        raise ValueError(f"Invalid month format '{month}', expected YYYY-MM")
    return int(parts[0]), int(parts[1])


def _format_line_item(position: int, label: str, amount: float, source_type: str,
                      category_id: str | None = None) -> str:
    """Format a single line item for text output."""
    source = f"[{source_type}"
    if category_id:
        source += f", {category_id}"
    source += "]"
    return f"  Pos {position}: {label:<40s} {format_eur(amount):>15s}  {source}"


def _format_preview(preview: InvoicePreview, title: str,
                    invoice: GeneratedInvoice | None = None) -> str:
    """Format a full preview into human-readable text."""
    lines = [title, ""]
    lines.append("Positionen:")
    for item in preview.items:
        lines.append(_format_line_item(
            item.position, item.label, item.amount,
            item.source_type, item.category_id,
        ))
        for w in item.warnings:
            lines.append(f"    ⚠ {w}")

    lines.append("")
    lines.append(f"Netto-Rechnungsbetrag:  {format_eur(preview.net_total):>15s}")
    lines.append(f"Umsatzsteuer (19%):     {format_eur(preview.vat_amount):>15s}")
    lines.append(f"Brutto-Rechnungsbetrag: {format_eur(preview.gross_total):>15s}")

    if invoice:
        lines.append("")
        lines.append(f"Rechnung: {invoice.invoice_number} (Status: {invoice.status})")
        if invoice.pdf_path:
            lines.append(f"PDF: {invoice.pdf_path}")
    else:
        lines.append("")
        lines.append("Rechnung: nicht generiert")

    if preview.warnings:
        lines.append("")
        lines.append("Hinweise:")
        for w in preview.warnings:
            lines.append(f"  - {w}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool 1: get_invoice_status
# ---------------------------------------------------------------------------
@mcp.tool()
def get_invoice_status(
    invoice_number: str | None = None,
    invoice_id: int | None = None,
    month: str | None = None,
    client_id: str = "drs",
) -> str:
    """Get the status and details of a specific generated invoice.

    Provide invoice_number (e.g. '202501-02'), invoice_id, or month (e.g. '2025-01').
    """
    try:
        with get_session() as db:
            inv = None
            if invoice_number:
                inv = db.query(GeneratedInvoice).filter(
                    GeneratedInvoice.invoice_number == invoice_number
                ).first()
            elif invoice_id:
                inv = db.get(GeneratedInvoice, invoice_id)
            elif month:
                year, mon = _parse_month(month)
                inv = db.query(GeneratedInvoice).filter(and_(
                    GeneratedInvoice.period_year == year,
                    GeneratedInvoice.period_month == mon,
                    GeneratedInvoice.client_id == client_id,
                )).first()
            else:
                return "Fehler: Bitte invoice_number, invoice_id oder month angeben."

            if not inv:
                return "Keine Rechnung gefunden."

            items = db.query(GeneratedInvoiceItem).filter(
                GeneratedInvoiceItem.invoice_id == inv.id
            ).order_by(GeneratedInvoiceItem.position).all()

            lines = [
                f"Rechnung {inv.invoice_number}",
                f"  Status: {inv.status}",
                f"  Leistungszeitraum: {format_month_year(inv.period_year, inv.period_month)}",
                f"  Rechnungsdatum: {format_date_german(inv.invoice_date)}",
                f"  Netto:  {format_eur(inv.net_total):>15s}",
                f"  USt 19%: {format_eur(inv.vat_amount):>14s}",
                f"  Brutto: {format_eur(inv.gross_total):>14s}",
                f"  Positionen: {len(items)}",
            ]
            for item in items:
                lines.append(f"    Pos {item.position}: {item.label:<35s} {format_eur(item.amount):>15s}")
            if inv.pdf_path:
                lines.append(f"  PDF: {inv.pdf_path}")
            if inv.notes:
                lines.append(f"  Notizen: {inv.notes}")

            # Payment info
            payments = db.query(PaymentReceipt).filter(
                PaymentReceipt.matched_invoice_id == inv.id
            ).all()
            if payments:
                total_paid = sum(p.amount_eur for p in payments)
                lines.append(f"  Zahlungen: {len(payments)} ({format_eur(total_paid)})")

            return "\n".join(lines)
    except Exception as e:
        return f"Fehler: {e}"


# ---------------------------------------------------------------------------
# Tool 2: get_month_overview
# ---------------------------------------------------------------------------
@mcp.tool()
def get_month_overview(month: str, client_id: str = "drs") -> str:
    """Get a complete overview of a billing month including all resolved line items and totals.

    Args:
        month: Billing month in YYYY-MM format (e.g., '2025-01')
        client_id: Client ID (default: 'drs')
    """
    try:
        year, mon = _parse_month(month)
        with get_session() as db:
            preview = preview_invoice(client_id, year, mon, db)
            title = f"Monatsübersicht: {format_month_year(year, mon)}"

            # Check if invoice exists
            inv = db.query(GeneratedInvoice).filter(and_(
                GeneratedInvoice.period_year == year,
                GeneratedInvoice.period_month == mon,
                GeneratedInvoice.client_id == client_id,
            )).first()

            return _format_preview(preview, title, inv)
    except Exception as e:
        return f"Fehler: {e}"


# ---------------------------------------------------------------------------
# Tool 3: get_open_invoices
# ---------------------------------------------------------------------------
@mcp.tool()
def get_open_invoices(client_id: str | None = None) -> str:
    """List all invoices that are not yet paid (status: draft, sent, or overdue)."""
    try:
        with get_session() as db:
            query = db.query(GeneratedInvoice).filter(
                GeneratedInvoice.status != "paid"
            )
            if client_id:
                query = query.filter(GeneratedInvoice.client_id == client_id)
            invoices = query.order_by(
                GeneratedInvoice.period_year.desc(),
                GeneratedInvoice.period_month.desc(),
            ).all()

            if not invoices:
                return "Keine offenen Rechnungen."

            lines = [f"Offene Rechnungen ({len(invoices)}):"]
            for inv in invoices:
                period = format_month_year(inv.period_year, inv.period_month)
                lines.append(
                    f"  {inv.invoice_number}  {period:<20s}  "
                    f"{format_eur(inv.gross_total):>15s}  [{inv.status}]"
                )
            return "\n".join(lines)
    except Exception as e:
        return f"Fehler: {e}"


# ---------------------------------------------------------------------------
# Tool 4: get_category_costs
# ---------------------------------------------------------------------------
@mcp.tool()
def get_category_costs(
    category_id: str,
    from_month: str | None = None,
    to_month: str | None = None,
) -> str:
    """Get costs for a specific cost category, optionally filtered by month range.

    Args:
        category_id: Cost category ID (e.g., 'junior_fm', 'cloud_engineer', 'upwork_mobile', 'aeologic')
        from_month: Start month in YYYY-MM format (inclusive)
        to_month: End month in YYYY-MM format (inclusive)
    """
    try:
        with get_session() as db:
            category = db.get(CostCategory, category_id)
            if not category:
                return f"Fehler: Kategorie '{category_id}' nicht gefunden."

            lines = [
                f"Kategorie: {category.name}",
                f"  Anbieter: {category.provider_name or '-'}",
                f"  Kostentyp: {category.cost_type}",
                f"  Währung: {category.currency}",
                f"  Abrechnungszyklus: {category.billing_cycle}",
                "",
            ]

            if category.cost_type == "upwork":
                # Upwork: query transactions grouped by month
                query = db.query(UpworkTransaction).filter(
                    UpworkTransaction.category_id == category_id
                )
                if from_month:
                    query = query.filter(UpworkTransaction.assigned_month >= from_month)
                if to_month:
                    query = query.filter(UpworkTransaction.assigned_month <= to_month)
                txns = query.order_by(UpworkTransaction.assigned_month).all()

                if not txns:
                    lines.append("Keine Upwork-Transaktionen gefunden.")
                else:
                    # Group by month
                    months: dict[str, list] = {}
                    for tx in txns:
                        m = tx.assigned_month or "unbekannt"
                        months.setdefault(m, []).append(tx)

                    lines.append("Upwork-Transaktionen:")
                    total = 0.0
                    for m_key in sorted(months):
                        m_txns = months[m_key]
                        m_total = sum(t.amount_eur for t in m_txns)
                        total += m_total
                        lines.append(f"  {m_key}: {format_eur(m_total):>15s} ({len(m_txns)} Transaktionen)")
                    lines.append(f"  Gesamt: {format_eur(total):>15s}")
            else:
                # Provider invoices
                query = db.query(ProviderInvoice).filter(
                    ProviderInvoice.category_id == category_id
                )
                if from_month:
                    query = query.filter(ProviderInvoice.assigned_month >= from_month)
                if to_month:
                    query = query.filter(ProviderInvoice.assigned_month <= to_month)
                invoices = query.order_by(ProviderInvoice.assigned_month).all()

                if not invoices:
                    lines.append("Keine Rechnungen gefunden.")
                else:
                    lines.append("Rechnungen:")
                    total = 0.0
                    for inv in invoices:
                        bank_tx = db.query(BankTransaction).filter(
                            BankTransaction.provider_invoice_id == inv.id
                        ).first()
                        bank_info = ""
                        if bank_tx:
                            bank_info = f"  Bank: {format_eur(abs(bank_tx.amount_eur))}"
                        lines.append(
                            f"  {inv.assigned_month or '-'}: {inv.invoice_number:<20s} "
                            f"{format_eur(inv.amount):>15s}{bank_info}"
                        )
                        total += inv.amount
                    lines.append(f"  Gesamt: {format_eur(total):>15s}")

            return "\n".join(lines)
    except Exception as e:
        return f"Fehler: {e}"


# ---------------------------------------------------------------------------
# Tool 5: get_reconciliation
# ---------------------------------------------------------------------------
@mcp.tool()
def get_reconciliation(month: str) -> str:
    """Show reconciliation status: provider invoices vs bank payments for a month.

    Args:
        month: Billing month in YYYY-MM format (e.g., '2025-01')
    """
    try:
        year, mon = _parse_month(month)
        with get_session() as db:
            recon = reconcile_month(year, mon, db)

            lines = [f"Abstimmung: {format_month_year(year, mon)}", ""]
            lines.append("Lieferantenrechnungen vs. Bankzahlungen:")

            for m in recon.provider_matches:
                status = "✓ verknüpft" if m.has_bank_payment else "✗ keine Bankzahlung"
                lines.append(
                    f"  [{m.category_id}] {m.invoice_number}: "
                    f"{format_eur(m.invoice_amount):>15s}  {status}"
                )

            lines.append(
                f"\n  Verknüpft: {recon.matched_count}, Offen: {recon.unmatched_count}"
            )

            if recon.unmatched_bank_transactions:
                lines.append("\nNicht zugeordnete Bankzahlungen:")
                for tx in recon.unmatched_bank_transactions:
                    lines.append(
                        f"  {format_date_german(tx.booking_date)}: "
                        f"{format_eur(tx.amount_eur):>15s}  {tx.description[:50]}"
                    )

            lines.append("")
            if recon.invoice_status:
                s = recon.invoice_status
                lines.append(f"Rechnung: {s.invoice_number} (Status: {s.status})")
                if s.total_paid > 0:
                    lines.append(f"Zahlungseingang: {format_eur(s.total_paid)}")
                else:
                    lines.append("Zahlungseingang: keiner")
            else:
                lines.append("Rechnung: nicht generiert")

            return "\n".join(lines)
    except Exception as e:
        return f"Fehler: {e}"


# ---------------------------------------------------------------------------
# Tool 6: get_missing_data
# ---------------------------------------------------------------------------
@mcp.tool()
def get_missing_data(month: str, client_id: str = "drs") -> str:
    """Find data gaps for a billing month: missing provider invoices, unmatched transactions, etc.

    Args:
        month: Billing month in YYYY-MM format (e.g., '2025-01')
        client_id: Client ID (default: 'drs')
    """
    try:
        year, mon = _parse_month(month)
        month_str = f"{year}-{mon:02d}"
        with get_session() as db:
            lines = [f"Fehlende Daten: {format_month_year(year, mon)}", ""]
            issues: list[str] = []

            definitions = db.query(LineItemDefinition).filter(
                LineItemDefinition.client_id == client_id
            ).order_by(LineItemDefinition.sort_order, LineItemDefinition.position).all()

            for defn in definitions:
                if defn.source_type == "fixed":
                    if defn.fixed_amount is None:
                        issues.append(f"Pos {defn.position} ({defn.label}): fixed_amount nicht gesetzt")
                elif defn.source_type == "category" and defn.category_id:
                    category = db.get(CostCategory, defn.category_id)
                    if not category:
                        issues.append(f"Pos {defn.position} ({defn.label}): Kategorie '{defn.category_id}' nicht gefunden")
                        continue

                    if category.cost_type in ("direct", "distributed"):
                        # Check provider invoice
                        if category.cost_type == "direct":
                            inv = db.query(ProviderInvoice).filter(and_(
                                ProviderInvoice.category_id == defn.category_id,
                                ProviderInvoice.assigned_month == month_str,
                            )).first()
                        else:
                            # distributed: check covers_months
                            all_invs = db.query(ProviderInvoice).filter(
                                ProviderInvoice.category_id == defn.category_id
                            ).all()
                            inv = None
                            for i in all_invs:
                                if month_str in i.covers_months:
                                    inv = i
                                    break

                        if not inv:
                            issues.append(
                                f"Pos {defn.position} ({defn.label}): "
                                f"Keine Rechnung für {month_str} [{category.cost_type}]"
                            )
                        else:
                            # Check bank transaction link
                            bank_tx = db.query(BankTransaction).filter(
                                BankTransaction.provider_invoice_id == inv.id
                            ).first()
                            if not bank_tx and (
                                category.currency == "USD"
                                or category.cost_type == "distributed"
                            ):
                                issues.append(
                                    f"Pos {defn.position} ({defn.label}): "
                                    f"Rechnung {inv.invoice_number} ohne Bankzahlung"
                                )

                    elif category.cost_type == "upwork":
                        txns = db.query(UpworkTransaction).filter(
                            UpworkTransaction.assigned_month == month_str
                        ).count()
                        if txns == 0:
                            issues.append(
                                f"Pos {defn.position} ({defn.label}): "
                                f"Keine Upwork-Transaktionen für {month_str}"
                            )

            # Check invoice generation
            gen_inv = db.query(GeneratedInvoice).filter(and_(
                GeneratedInvoice.period_year == year,
                GeneratedInvoice.period_month == mon,
                GeneratedInvoice.client_id == client_id,
            )).first()

            if not gen_inv:
                issues.append("Rechnung noch nicht generiert")
            else:
                payments = db.query(PaymentReceipt).filter(
                    PaymentReceipt.matched_invoice_id == gen_inv.id
                ).count()
                if payments == 0 and gen_inv.status != "paid":
                    issues.append(f"Rechnung {gen_inv.invoice_number}: kein Zahlungseingang")

            if not issues:
                lines.append("Keine fehlenden Daten gefunden. Alle Positionen sind vollständig.")
            else:
                for issue in issues:
                    lines.append(f"  - {issue}")

            return "\n".join(lines)
    except Exception as e:
        return f"Fehler: {e}"


# ---------------------------------------------------------------------------
# Tool 7: get_upwork_summary
# ---------------------------------------------------------------------------
@mcp.tool()
def get_upwork_summary(month: str) -> str:
    """Get Upwork transaction summary for a specific month.

    Args:
        month: Month in YYYY-MM format (e.g., '2025-01')
    """
    try:
        year, mon = _parse_month(month)
        month_str = f"{year}-{mon:02d}"
        with get_session() as db:
            txns = db.query(UpworkTransaction).filter(
                UpworkTransaction.assigned_month == month_str
            ).order_by(UpworkTransaction.tx_date).all()

            lines = [f"Upwork-Zusammenfassung: {format_month_year(year, mon)}", ""]

            if not txns:
                lines.append("Keine Upwork-Transaktionen für diesen Monat.")
                return "\n".join(lines)

            total = 0.0
            lines.append("Transaktionen:")
            for tx in txns:
                date_str = format_date_german(tx.tx_date) if tx.tx_date else "-"
                desc = (tx.description or "-")[:50]
                lines.append(f"  {date_str}  {format_eur(tx.amount_eur):>12s}  {desc}")
                total += tx.amount_eur

            lines.append("")
            lines.append(f"Anzahl: {len(txns)}")
            lines.append(f"Summe: {format_eur(total)}")

            return "\n".join(lines)
    except Exception as e:
        return f"Fehler: {e}"


# ---------------------------------------------------------------------------
# Tool 8: search_transactions
# ---------------------------------------------------------------------------
@mcp.tool()
def search_transactions(
    query: str,
    transaction_type: str | None = None,
    limit: int = 20,
) -> str:
    """Search bank and/or upwork transactions by keyword in the description.

    Args:
        query: Search keyword (searches description/Buchungstext)
        transaction_type: Optional filter: 'bank', 'upwork', or None for both
        limit: Maximum results per type (default: 20)
    """
    try:
        with get_session() as db:
            lines = [f"Suche: \"{query}\"", ""]
            pattern = f"%{query}%"

            if transaction_type in (None, "bank"):
                bank_txns = db.query(BankTransaction).filter(
                    BankTransaction.description.ilike(pattern)
                ).limit(limit).all()
                lines.append(f"Banktransaktionen ({len(bank_txns)}):")
                if bank_txns:
                    for tx in bank_txns:
                        cat = f"[{tx.category_id}]" if tx.category_id else "[--]"
                        lines.append(
                            f"  {format_date_german(tx.booking_date)}  "
                            f"{format_eur(abs(tx.amount_eur)):>12s}  {cat}  "
                            f"{tx.description[:60]}"
                        )
                else:
                    lines.append("  (keine Treffer)")
                lines.append("")

            if transaction_type in (None, "upwork"):
                upwork_txns = db.query(UpworkTransaction).filter(
                    UpworkTransaction.description.ilike(pattern)
                ).limit(limit).all()
                lines.append(f"Upwork-Transaktionen ({len(upwork_txns)}):")
                if upwork_txns:
                    for tx in upwork_txns:
                        date_str = format_date_german(tx.tx_date) if tx.tx_date else "-"
                        lines.append(
                            f"  {date_str}  {format_eur(tx.amount_eur):>12s}  "
                            f"[{tx.assigned_month or '-'}]  {(tx.description or '-')[:60]}"
                        )
                else:
                    lines.append("  (keine Treffer)")

            return "\n".join(lines)
    except Exception as e:
        return f"Fehler: {e}"


# ---------------------------------------------------------------------------
# Tool 9: get_working_days
# ---------------------------------------------------------------------------
@mcp.tool()
def get_working_days(year: int, month: int) -> str:
    """Get the number of working days (Mon-Fri, excluding Hessen holidays) for a month.

    Args:
        year: Year (e.g., 2025)
        month: Month (1-12)
    """
    try:
        days = working_days_in_month(year, month)
        label = format_month_year(year, month)
        return f"{label}: {days} Arbeitstage"
    except Exception as e:
        return f"Fehler: {e}"


# ---------------------------------------------------------------------------
# Tool 10: get_distribution
# ---------------------------------------------------------------------------
@mcp.tool()
def get_distribution(total_amount: float, months: list[str]) -> str:
    """Calculate how a total amount is distributed across months by Hessen working days.

    Args:
        total_amount: Total EUR amount to distribute
        months: List of months in YYYY-MM format (e.g., ['2025-01', '2025-02', '2025-03'])
    """
    try:
        month_tuples = [_parse_month(m) for m in months]
        distribution = distribute_cost_by_working_days(total_amount, month_tuples)

        lines = [f"Verteilung von {format_eur(total_amount)} auf {len(months)} Monate:", ""]
        total_days = sum(working_days_in_month(y, m) for y, m in month_tuples)
        allocated_total = 0.0

        for y, m in month_tuples:
            days = working_days_in_month(y, m)
            amount = float(distribution[(y, m)])
            allocated_total += amount
            label = format_month_year(y, m)
            lines.append(f"  {label:<20s}  {days:>2d} Tage  {format_eur(amount):>15s}")

        lines.append("")
        lines.append(f"  Arbeitstage gesamt: {total_days}")
        lines.append(f"  Verteilte Summe: {format_eur(allocated_total)}")

        return "\n".join(lines)
    except Exception as e:
        return f"Fehler: {e}"
