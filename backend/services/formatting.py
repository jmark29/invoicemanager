"""German formatting utilities for currency, dates, and invoice periods.

All monetary calculations use Decimal with ROUND_HALF_UP to match the
reference implementation in generate_invoice.py:51-64.
"""

from calendar import monthrange
from datetime import date
from decimal import ROUND_HALF_UP, Decimal


def round_currency(amount: float) -> Decimal:
    """Round a monetary amount to 2 decimal places using ROUND_HALF_UP."""
    return Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def format_eur(amount: float) -> str:
    """Format a number as German EUR string: ``1.234,56 €``.

    Uses Decimal internally to avoid float rounding artifacts.
    """
    d = round_currency(amount)
    int_part = int(d)
    dec_part = abs(d - int_part)
    dec_str = f"{dec_part:.2f}"[2:]  # extract 2 decimal digits

    # Add thousand separators (German style: period)
    int_str = f"{abs(int_part):,}".replace(",", ".")
    if int_part < 0:
        int_str = "-" + int_str

    return f"{int_str},{dec_str} \u20ac"


def format_date_german(d: date) -> str:
    """Format a date as DD.MM.YYYY (German convention)."""
    return f"{d.day:02d}.{d.month:02d}.{d.year}"


def format_period(year: int, month: int) -> str:
    """Return the service period string, e.g. ``01.01.2025 bis 31.01.2025``."""
    last_day = monthrange(year, month)[1]
    return f"01.{month:02d}.{year} bis {last_day:02d}.{month:02d}.{year}"


def format_month_year(year: int, month: int) -> str:
    """Return a human-readable month label, e.g. ``Januar 2025``."""
    month_names = [
        "", "Januar", "Februar", "März", "April", "Mai", "Juni",
        "Juli", "August", "September", "Oktober", "November", "Dezember",
    ]
    return f"{month_names[month]} {year}"


def invoice_number(year: int, month: int, client_number: str) -> str:
    """Generate an invoice number like ``202501-02``."""
    return f"{year}{month:02d}-{client_number}"


def invoice_filename(year: int, month: int, client_number: str) -> str:
    """Generate the invoice filename with AR prefix, e.g. ``AR202501-02.pdf``."""
    return f"AR{year}{month:02d}-{client_number}.pdf"
