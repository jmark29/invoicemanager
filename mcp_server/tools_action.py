"""Action tools (DB writes) for the Invoice Manager MCP server."""

from datetime import date

from backend.models.bank_transaction import BankTransaction
from backend.models.client import Client
from backend.models.cost_category import CostCategory
from backend.models.generated_invoice import GeneratedInvoice
from backend.models.payment_receipt import PaymentReceipt
from backend.models.provider_invoice import ProviderInvoice
from backend.services.formatting import (
    format_date_german,
    format_eur,
    format_month_year,
    invoice_number as make_invoice_number,
)
from backend.services.invoice_engine import generate_invoice as _generate_invoice
from backend.services.bank_import import import_bank_transactions
from backend.services.upwork_import import import_upwork_transactions
from mcp_server.db import get_session
from mcp_server.server import mcp


def _parse_date(date_str: str) -> date:
    """Parse 'YYYY-MM-DD' into a date object."""
    return date.fromisoformat(date_str)


def _parse_month(month: str) -> tuple[int, int]:
    """Parse 'YYYY-MM' into (year, month)."""
    parts = month.strip().split("-")
    if len(parts) != 2:
        raise ValueError(f"Invalid month format '{month}', expected YYYY-MM")
    return int(parts[0]), int(parts[1])


# ---------------------------------------------------------------------------
# Tool 1: generate_invoice
# ---------------------------------------------------------------------------
@mcp.tool()
def generate_invoice(
    month: str,
    client_id: str = "drs",
    invoice_number: str | None = None,
    invoice_date: str | None = None,
    overrides: dict[int, float] | None = None,
    notes: str | None = None,
) -> str:
    """Generate a monthly invoice (resolve amounts, render HTML/PDF, save to DB).

    Args:
        month: Billing month in YYYY-MM format (e.g., '2025-01')
        client_id: Client ID (default: 'drs')
        invoice_number: Invoice number (default: auto-generated, e.g., '202501-02')
        invoice_date: Invoice date in YYYY-MM-DD format (default: today)
        overrides: Optional dict mapping position number to override amount (e.g., {4: 2851.20})
        notes: Optional notes to store with the invoice
    """
    try:
        year, mon = _parse_month(month)

        with get_session() as db:
            # Derive defaults
            client = db.get(Client, client_id)
            if not client:
                return f"Fehler: Client '{client_id}' nicht gefunden."

            inv_number = invoice_number or make_invoice_number(year, mon, client.client_number)
            inv_date = _parse_date(invoice_date) if invoice_date else date.today()

            invoice = _generate_invoice(
                client_id=client_id,
                year=year,
                month=mon,
                invoice_number=inv_number,
                invoice_date=inv_date,
                overrides=overrides,
                notes=notes,
                db=db,
            )

            return (
                f"Rechnung erfolgreich generiert!\n"
                f"  Nummer: {invoice.invoice_number}\n"
                f"  Zeitraum: {format_month_year(year, mon)}\n"
                f"  Datum: {format_date_german(invoice.invoice_date)}\n"
                f"  Netto:  {format_eur(invoice.net_total)}\n"
                f"  USt 19%: {format_eur(invoice.vat_amount)}\n"
                f"  Brutto: {format_eur(invoice.gross_total)}\n"
                f"  Status: {invoice.status}\n"
                f"  PDF: {invoice.pdf_path}"
            )
    except ValueError as e:
        return f"Fehler: {e}"
    except Exception as e:
        return f"Unerwarteter Fehler: {type(e).__name__}: {e}"


# ---------------------------------------------------------------------------
# Tool 2: import_upwork_xlsx
# ---------------------------------------------------------------------------
@mcp.tool()
def import_upwork_xlsx(
    file_path: str,
    category_id: str = "upwork_mobile",
) -> str:
    """Import Upwork transactions from an XLSX file.

    Args:
        file_path: Path to the Upwork XLSX file
        category_id: Cost category to assign (default: 'upwork_mobile')
    """
    try:
        with get_session() as db:
            result = import_upwork_transactions(file_path, db, category_id=category_id)

            lines = [
                "Upwork-Import abgeschlossen:",
                f"  Importiert: {result.imported}",
                f"  Duplikate übersprungen: {result.skipped_duplicate}",
                f"  Ohne Betrag übersprungen: {result.skipped_no_amount}",
                f"  Ohne Periode übersprungen: {result.skipped_no_period}",
            ]
            if result.errors:
                lines.append(f"  Fehler: {len(result.errors)}")
                for err in result.errors[:5]:
                    lines.append(f"    - {err}")
            return "\n".join(lines)
    except Exception as e:
        return f"Fehler: {e}"


# ---------------------------------------------------------------------------
# Tool 3: import_bank_statement
# ---------------------------------------------------------------------------
@mcp.tool()
def import_bank_statement(file_path: str) -> str:
    """Import bank transactions from a bank statement XLSX file.

    Args:
        file_path: Path to the bank statement XLSX file
    """
    try:
        with get_session() as db:
            result = import_bank_transactions(file_path, db)

            lines = [
                "Bank-Import abgeschlossen:",
                f"  Importiert: {result.imported}",
                f"  Duplikate übersprungen: {result.skipped_duplicate}",
                f"  Automatisch zugeordnet: {result.auto_matched}",
            ]
            if result.errors:
                lines.append(f"  Fehler: {len(result.errors)}")
                for err in result.errors[:5]:
                    lines.append(f"    - {err}")
            return "\n".join(lines)
    except Exception as e:
        return f"Fehler: {e}"


# ---------------------------------------------------------------------------
# Tool 4: create_provider_invoice (renamed from record_provider_invoice)
# ---------------------------------------------------------------------------
@mcp.tool()
def create_provider_invoice(
    category_id: str,
    invoice_number: str,
    invoice_date: str,
    amount: float,
    assigned_month: str | None = None,
    currency: str = "EUR",
    hours: float | None = None,
    hourly_rate: float | None = None,
    rate_currency: str | None = None,
    period_start: str | None = None,
    period_end: str | None = None,
    covers_months: list[str] | None = None,
    notes: str | None = None,
) -> str:
    """Create a new provider invoice record and auto-match against bank transactions.

    Args:
        category_id: Cost category ID (e.g., 'junior_fm', 'aeologic')
        invoice_number: Provider's invoice number
        invoice_date: Invoice date in YYYY-MM-DD format
        amount: Invoice amount
        assigned_month: Billing month in YYYY-MM format (defaults to invoice_date month)
        currency: Currency code (default: 'EUR')
        hours: Optional hours worked
        hourly_rate: Optional hourly rate
        rate_currency: Optional currency for hourly rate
        period_start: Optional service period start in YYYY-MM-DD format
        period_end: Optional service period end in YYYY-MM-DD format
        covers_months: For distributed invoices, list of months covered (YYYY-MM format)
        notes: Optional notes
    """
    try:
        inv_date = _parse_date(invoice_date)
        with get_session() as db:
            category = db.get(CostCategory, category_id)
            if not category:
                return f"Fehler: Kategorie '{category_id}' nicht gefunden."

            month_str = assigned_month or f"{inv_date.year}-{inv_date.month:02d}"

            invoice = ProviderInvoice(
                category_id=category_id,
                invoice_number=invoice_number,
                invoice_date=inv_date,
                assigned_month=month_str,
                amount=amount,
                currency=currency,
                hours=hours,
                hourly_rate=hourly_rate,
                rate_currency=rate_currency,
                period_start=_parse_date(period_start) if period_start else None,
                period_end=_parse_date(period_end) if period_end else None,
                notes=notes,
            )
            if covers_months:
                invoice.covers_months = covers_months

            db.add(invoice)
            db.commit()
            db.refresh(invoice)

            # Auto-match against existing bank transactions
            from backend.services.transaction_matching import auto_match_after_invoice_creation
            match = auto_match_after_invoice_creation(invoice.id, db)
            db.refresh(invoice)

            match_info = ""
            if match:
                if match.confidence >= 0.95:
                    match_info = f"\n  Auto-Match: Transaktion #{match.bank_transaction_id} (Konfidenz {match.confidence:.0%})"
                else:
                    match_info = f"\n  Vorgeschlagener Match: Transaktion #{match.bank_transaction_id} (Konfidenz {match.confidence:.0%})"

            return (
                f"Rechnung erfasst:\n"
                f"  ID: {invoice.id}\n"
                f"  Kategorie: {category.name}\n"
                f"  Rechnungsnr.: {invoice.invoice_number}\n"
                f"  Datum: {format_date_german(inv_date)}\n"
                f"  Betrag: {format_eur(amount)}\n"
                f"  Zugeordneter Monat: {month_str}"
                f"{match_info}"
            )
    except Exception as e:
        return f"Fehler: {e}"


# ---------------------------------------------------------------------------
# Tool 4b: create_provider_invoices_bulk
# ---------------------------------------------------------------------------
@mcp.tool()
def create_provider_invoices_bulk(
    invoices: list[dict],
) -> str:
    """Create multiple provider invoice records in one call.

    Args:
        invoices: List of invoice dicts, each with keys: category_id, invoice_number,
                  invoice_date (YYYY-MM-DD), amount. Optional: assigned_month, currency,
                  hours, hourly_rate, covers_months, notes.
    """
    try:
        results = []
        errors = []
        for i, inv_data in enumerate(invoices):
            try:
                result = create_provider_invoice(
                    category_id=inv_data["category_id"],
                    invoice_number=inv_data["invoice_number"],
                    invoice_date=inv_data["invoice_date"],
                    amount=inv_data["amount"],
                    assigned_month=inv_data.get("assigned_month"),
                    currency=inv_data.get("currency", "EUR"),
                    hours=inv_data.get("hours"),
                    hourly_rate=inv_data.get("hourly_rate"),
                    covers_months=inv_data.get("covers_months"),
                    notes=inv_data.get("notes"),
                )
                results.append(result)
            except Exception as e:
                errors.append(f"#{i+1} ({inv_data.get('invoice_number', '?')}): {e}")

        lines = [f"Bulk-Import: {len(results)} von {len(invoices)} erfolgreich erstellt."]
        if errors:
            lines.append(f"\nFehler ({len(errors)}):")
            for err in errors:
                lines.append(f"  - {err}")
        return "\n".join(lines)
    except Exception as e:
        return f"Fehler: {e}"


# ---------------------------------------------------------------------------
# Tool 4c: match_transaction_to_invoice
# ---------------------------------------------------------------------------
@mcp.tool()
def match_transaction_to_invoice(
    bank_transaction_id: int,
    provider_invoice_id: int,
    bank_fee: float | None = None,
) -> str:
    """Manually match a bank transaction to a provider invoice. Computes FX rate and bank fees.

    Args:
        bank_transaction_id: ID of the bank transaction
        provider_invoice_id: ID of the provider invoice
        bank_fee: Optional bank fee override (EUR)
    """
    try:
        from backend.services.transaction_matching import apply_match

        with get_session() as db:
            tx = db.get(BankTransaction, bank_transaction_id)
            if not tx:
                return f"Fehler: Banktransaktion {bank_transaction_id} nicht gefunden."
            inv = db.get(ProviderInvoice, provider_invoice_id)
            if not inv:
                return f"Fehler: Lieferantenrechnung {provider_invoice_id} nicht gefunden."

            result = apply_match(
                bank_transaction_id=bank_transaction_id,
                provider_invoice_id=provider_invoice_id,
                db=db,
                match_type="manual",
                bank_fee_override=bank_fee,
            )

            lines = [
                "Match hergestellt:",
                f"  Transaktion #{tx.id}: {format_date_german(tx.booking_date)} {format_eur(abs(tx.amount_eur))}",
                f"  Rechnung: {inv.invoice_number} ({format_eur(inv.amount)} {inv.currency})",
                f"  Betrag EUR: {format_eur(result['amount_eur'])}",
            ]
            if result["fx_rate"] and result["fx_rate"] != 1.0:
                lines.append(f"  FX-Kurs: {result['fx_rate']:.6f}")
            if result["bank_fee"] is not None:
                lines.append(f"  Bankgebühr: {format_eur(result['bank_fee'])}")

            return "\n".join(lines)
    except Exception as e:
        return f"Fehler: {e}"


# ---------------------------------------------------------------------------
# Tool 5: link_bank_payment (legacy — delegates to match_transaction_to_invoice)
# ---------------------------------------------------------------------------
@mcp.tool()
def link_bank_payment(
    bank_transaction_id: int,
    provider_invoice_id: int,
) -> str:
    """Link a bank transaction to a provider invoice for reconciliation.
    Uses the matching service for proper FX/fee computation.

    Args:
        bank_transaction_id: ID of the bank transaction
        provider_invoice_id: ID of the provider invoice
    """
    return match_transaction_to_invoice(bank_transaction_id, provider_invoice_id)


# ---------------------------------------------------------------------------
# Tool 6: record_payment
# ---------------------------------------------------------------------------
@mcp.tool()
def record_payment(
    client_id: str,
    amount: float,
    payment_date: str,
    reference: str | None = None,
    invoice_id: int | None = None,
    notes: str | None = None,
) -> str:
    """Record a client payment receipt.

    Args:
        client_id: Client ID (e.g., 'drs')
        amount: Payment amount in EUR
        payment_date: Payment date in YYYY-MM-DD format
        reference: Optional payment reference
        invoice_id: Optional invoice ID to match this payment to
        notes: Optional notes
    """
    try:
        pay_date = _parse_date(payment_date)
        with get_session() as db:
            client = db.get(Client, client_id)
            if not client:
                return f"Fehler: Client '{client_id}' nicht gefunden."

            if invoice_id:
                invoice = db.get(GeneratedInvoice, invoice_id)
                if not invoice:
                    return f"Fehler: Rechnung {invoice_id} nicht gefunden."

            payment = PaymentReceipt(
                client_id=client_id,
                payment_date=pay_date,
                amount_eur=amount,
                reference=reference,
                matched_invoice_id=invoice_id,
                notes=notes,
            )
            db.add(payment)
            db.commit()
            db.refresh(payment)

            lines = [
                "Zahlungseingang erfasst:",
                f"  ID: {payment.id}",
                f"  Client: {client.name}",
                f"  Betrag: {format_eur(amount)}",
                f"  Datum: {format_date_german(pay_date)}",
            ]
            if reference:
                lines.append(f"  Referenz: {reference}")
            if invoice_id:
                lines.append(f"  Zugeordnete Rechnung: {invoice_id}")

            return "\n".join(lines)
    except Exception as e:
        return f"Fehler: {e}"


# ---------------------------------------------------------------------------
# Tool 7: update_invoice_status
# ---------------------------------------------------------------------------
VALID_STATUSES = {"draft", "sent", "paid", "overdue"}


@mcp.tool()
def update_invoice_status(
    status: str,
    invoice_id: int | None = None,
    invoice_number: str | None = None,
    sent_date: str | None = None,
) -> str:
    """Change the status of a generated invoice.

    Args:
        status: New status: 'draft', 'sent', 'paid', or 'overdue'
        invoice_id: Invoice ID (provide either this or invoice_number)
        invoice_number: Invoice number (e.g., '202501-02')
        sent_date: Date sent in YYYY-MM-DD format (optional, used when status='sent')
    """
    try:
        if status not in VALID_STATUSES:
            return f"Fehler: Ungültiger Status '{status}'. Erlaubt: {', '.join(sorted(VALID_STATUSES))}"

        with get_session() as db:
            invoice = None
            if invoice_id:
                invoice = db.get(GeneratedInvoice, invoice_id)
            elif invoice_number:
                invoice = db.query(GeneratedInvoice).filter(
                    GeneratedInvoice.invoice_number == invoice_number
                ).first()
            else:
                return "Fehler: Bitte invoice_id oder invoice_number angeben."

            if not invoice:
                return "Fehler: Rechnung nicht gefunden."

            old_status = invoice.status
            invoice.status = status

            if sent_date:
                invoice.sent_date = _parse_date(sent_date)
            elif status == "sent" and not invoice.sent_date:
                invoice.sent_date = date.today()

            db.commit()

            return (
                f"Status aktualisiert:\n"
                f"  Rechnung: {invoice.invoice_number}\n"
                f"  Status: {old_status} → {status}"
            )
    except Exception as e:
        return f"Fehler: {e}"
