"""MCP resource templates for the Invoice Manager server."""

from sqlalchemy import and_

from backend.models.bank_transaction import BankTransaction
from backend.models.client import Client
from backend.models.cost_category import CostCategory
from backend.models.generated_invoice import GeneratedInvoice
from backend.models.line_item_definition import LineItemDefinition
from backend.models.payment_receipt import PaymentReceipt
from backend.models.provider_invoice import ProviderInvoice
from backend.models.upwork_transaction import UpworkTransaction
from backend.services.formatting import format_date_german, format_eur, format_month_year
from backend.services.invoice_engine import preview_invoice
from mcp_server.db import get_session
from mcp_server.server import mcp


def _parse_month(month: str) -> tuple[int, int]:
    parts = month.strip().split("-")
    if len(parts) != 2:
        raise ValueError(f"Invalid month format '{month}', expected YYYY-MM")
    return int(parts[0]), int(parts[1])


# ---------------------------------------------------------------------------
# Resource 1: invoices://overview/{month}
# ---------------------------------------------------------------------------
@mcp.resource("invoices://overview/{month}")
def monthly_overview(month: str) -> str:
    """Monthly data overview including line items, totals, and invoice status."""
    try:
        year, mon = _parse_month(month)
        with get_session() as db:
            preview = preview_invoice("drs", year, mon, db)

            # Check for existing generated invoice
            inv = db.query(GeneratedInvoice).filter(and_(
                GeneratedInvoice.period_year == year,
                GeneratedInvoice.period_month == mon,
            )).first()

            lines = [
                f"# Monatsübersicht: {format_month_year(year, mon)}",
                "",
                "## Positionen",
                "",
                "| Pos | Bezeichnung | Betrag | Typ |",
                "|-----|-------------|--------|-----|",
            ]
            for item in preview.items:
                source = item.source_type
                if item.category_id:
                    source += f" ({item.category_id})"
                lines.append(
                    f"| {item.position} | {item.label} | {format_eur(item.amount)} | {source} |"
                )

            lines.extend([
                "",
                "## Summen",
                "",
                f"| | |",
                f"|---|---|",
                f"| Netto-Rechnungsbetrag | {format_eur(preview.net_total)} |",
                f"| Umsatzsteuer (19%) | {format_eur(preview.vat_amount)} |",
                f"| **Brutto-Rechnungsbetrag** | **{format_eur(preview.gross_total)}** |",
            ])

            if inv:
                lines.extend([
                    "",
                    "## Rechnung",
                    "",
                    f"- Nummer: {inv.invoice_number}",
                    f"- Status: {inv.status}",
                    f"- Datum: {format_date_german(inv.invoice_date)}",
                ])
                if inv.pdf_path:
                    lines.append(f"- PDF: {inv.pdf_path}")
            else:
                lines.extend(["", "## Rechnung", "", "*Noch nicht generiert*"])

            if preview.warnings:
                lines.extend(["", "## Hinweise", ""])
                for w in preview.warnings:
                    lines.append(f"- {w}")

            return "\n".join(lines)
    except Exception as e:
        return f"Fehler: {e}"


# ---------------------------------------------------------------------------
# Resource 2: invoices://client/{client_id}
# ---------------------------------------------------------------------------
@mcp.resource("invoices://client/{client_id}")
def client_info(client_id: str) -> str:
    """Client information and recent invoice history."""
    try:
        with get_session() as db:
            client = db.get(Client, client_id)
            if not client:
                return f"Client '{client_id}' nicht gefunden."

            lines = [
                f"# {client.name}",
                "",
                "## Stammdaten",
                "",
                f"- ID: {client.id}",
                f"- Kundennummer: {client.client_number}",
                f"- Adresse: {client.address_line1}",
            ]
            if client.address_line2:
                lines.append(f"- Adresszeile 2: {client.address_line2}")
            lines.extend([
                f"- PLZ/Ort: {client.zip_city}",
                f"- USt-Satz: {int(client.vat_rate * 100)}%",
                f"- Aktiv: {'Ja' if client.active else 'Nein'}",
            ])

            # Line item definitions
            definitions = db.query(LineItemDefinition).filter(
                LineItemDefinition.client_id == client_id
            ).order_by(LineItemDefinition.sort_order, LineItemDefinition.position).all()

            if definitions:
                lines.extend([
                    "",
                    "## Rechnungspositionen",
                    "",
                    "| Pos | Bezeichnung | Typ | Kategorie | Fixbetrag |",
                    "|-----|-------------|-----|-----------|-----------|",
                ])
                for d in definitions:
                    fixed = format_eur(d.fixed_amount) if d.fixed_amount else "-"
                    lines.append(
                        f"| {d.position} | {d.label} | {d.source_type} | "
                        f"{d.category_id or '-'} | {fixed} |"
                    )

            # Recent invoices
            invoices = db.query(GeneratedInvoice).filter(
                GeneratedInvoice.client_id == client_id
            ).order_by(
                GeneratedInvoice.period_year.desc(),
                GeneratedInvoice.period_month.desc(),
            ).limit(12).all()

            if invoices:
                lines.extend([
                    "",
                    "## Letzte Rechnungen",
                    "",
                    "| Nummer | Zeitraum | Brutto | Status |",
                    "|--------|----------|--------|--------|",
                ])
                for inv in invoices:
                    period = format_month_year(inv.period_year, inv.period_month)
                    lines.append(
                        f"| {inv.invoice_number} | {period} | "
                        f"{format_eur(inv.gross_total)} | {inv.status} |"
                    )

            # Payment summary
            payments = db.query(PaymentReceipt).filter(
                PaymentReceipt.client_id == client_id
            ).order_by(PaymentReceipt.payment_date.desc()).limit(10).all()

            if payments:
                lines.extend([
                    "",
                    "## Letzte Zahlungseingänge",
                    "",
                    "| Datum | Betrag | Referenz | Rechnung |",
                    "|-------|--------|----------|----------|",
                ])
                for p in payments:
                    inv_ref = str(p.matched_invoice_id) if p.matched_invoice_id else "-"
                    lines.append(
                        f"| {format_date_german(p.payment_date)} | "
                        f"{format_eur(p.amount_eur)} | {p.reference or '-'} | {inv_ref} |"
                    )

            return "\n".join(lines)
    except Exception as e:
        return f"Fehler: {e}"


# ---------------------------------------------------------------------------
# Resource 3: invoices://category/{category_id}
# ---------------------------------------------------------------------------
@mcp.resource("invoices://category/{category_id}")
def category_info(category_id: str) -> str:
    """Cost category details with recent transactions."""
    try:
        with get_session() as db:
            category = db.get(CostCategory, category_id)
            if not category:
                return f"Kategorie '{category_id}' nicht gefunden."

            lines = [
                f"# {category.name}",
                "",
                "## Details",
                "",
                f"- ID: {category.id}",
                f"- Anbieter: {category.provider_name or '-'}",
                f"- Standort: {category.provider_location or '-'}",
                f"- Kostentyp: {category.cost_type}",
                f"- Währung: {category.currency}",
                f"- Abrechnungszyklus: {category.billing_cycle}",
                f"- USt-Status: {category.vat_status}",
            ]
            if category.bank_keywords:
                lines.append(f"- Bank-Keywords: {', '.join(category.bank_keywords)}")
            if category.hourly_rate:
                lines.append(f"- Stundensatz: {category.hourly_rate} {category.rate_currency or ''}")

            # Provider invoices
            invoices = db.query(ProviderInvoice).filter(
                ProviderInvoice.category_id == category_id
            ).order_by(ProviderInvoice.invoice_date.desc()).limit(12).all()

            if invoices:
                lines.extend([
                    "",
                    "## Lieferantenrechnungen",
                    "",
                    "| Nr. | Datum | Monat | Betrag | Bankzahlung |",
                    "|-----|-------|-------|--------|-------------|",
                ])
                for inv in invoices:
                    bank_tx = db.query(BankTransaction).filter(
                        BankTransaction.provider_invoice_id == inv.id
                    ).first()
                    bank_info = format_eur(abs(bank_tx.amount_eur)) if bank_tx else "-"
                    lines.append(
                        f"| {inv.invoice_number} | {format_date_german(inv.invoice_date)} | "
                        f"{inv.assigned_month or '-'} | {format_eur(inv.amount)} | {bank_info} |"
                    )

            # Bank transactions
            bank_txns = db.query(BankTransaction).filter(
                BankTransaction.category_id == category_id
            ).order_by(BankTransaction.booking_date.desc()).limit(12).all()

            if bank_txns:
                lines.extend([
                    "",
                    "## Banktransaktionen",
                    "",
                    "| Datum | Betrag | Beschreibung | Rechnung |",
                    "|-------|--------|-------------|----------|",
                ])
                for tx in bank_txns:
                    inv_ref = str(tx.provider_invoice_id) if tx.provider_invoice_id else "-"
                    lines.append(
                        f"| {format_date_german(tx.booking_date)} | "
                        f"{format_eur(abs(tx.amount_eur))} | "
                        f"{tx.description[:40]} | {inv_ref} |"
                    )

            # Upwork transactions (if applicable)
            if category.cost_type == "upwork":
                upwork_txns = db.query(UpworkTransaction).filter(
                    UpworkTransaction.category_id == category_id
                ).order_by(UpworkTransaction.tx_date.desc()).limit(20).all()

                if upwork_txns:
                    lines.extend([
                        "",
                        "## Upwork-Transaktionen",
                        "",
                        "| Datum | Monat | Betrag | Beschreibung |",
                        "|-------|-------|--------|-------------|",
                    ])
                    for tx in upwork_txns:
                        date_str = format_date_german(tx.tx_date) if tx.tx_date else "-"
                        lines.append(
                            f"| {date_str} | {tx.assigned_month or '-'} | "
                            f"{format_eur(tx.amount_eur)} | {(tx.description or '-')[:40]} |"
                        )

            return "\n".join(lines)
    except Exception as e:
        return f"Fehler: {e}"
