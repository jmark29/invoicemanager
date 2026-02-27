"""Invoice renderer — Jinja2 HTML rendering + WeasyPrint PDF conversion.

Renders invoice data into an HTML page using the Jinja2 template at
``data/templates/invoice.html``, and optionally converts it to PDF via WeasyPrint.
"""

import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)

from backend.config import settings
from backend.services.formatting import format_date_german, format_eur, format_period


def _get_jinja_env() -> Environment:
    """Create a Jinja2 environment pointing at the templates directory."""
    return Environment(
        loader=FileSystemLoader(str(settings.TEMPLATES_DIR)),
        autoescape=True,
    )


def render_invoice_html(
    *,
    client_name: str,
    client_address_line1: str,
    client_zip_city: str,
    client_address_line2: str | None = None,
    invoice_number: str,
    invoice_date_str: str,
    period_str: str,
    items: list[dict],
    net_total: float,
    vat_amount: float,
    gross_total: float,
) -> str:
    """Render an invoice to an HTML string.

    Args:
        items: list of dicts with keys ``position``, ``label``, ``amount`` (float).
    """
    env = _get_jinja_env()
    template = env.get_template("invoice.html")

    # Format item amounts
    formatted_items = []
    for item in items:
        formatted_items.append({
            "position": item["position"],
            "label": item["label"],
            "amount_formatted": format_eur(item["amount"]),
        })

    return template.render(
        client_name=client_name,
        client_address_line1=client_address_line1,
        client_address_line2=client_address_line2,
        client_zip_city=client_zip_city,
        invoice_number=invoice_number,
        invoice_date=invoice_date_str,
        period=period_str,
        items=formatted_items,
        net_total=format_eur(net_total),
        vat_amount=format_eur(vat_amount),
        gross_total=format_eur(gross_total),
    )


def render_invoice_pdf(html: str) -> bytes:
    """Convert an invoice HTML string to a PDF byte string via WeasyPrint.

    The CSS file is resolved relative to the templates directory so that
    ``<link rel="stylesheet" href="invoice.css">`` works correctly.
    """
    from weasyprint import HTML  # lazy import to avoid startup cost

    base_url = str(settings.TEMPLATES_DIR) + "/"
    return HTML(string=html, base_url=base_url).write_pdf()


def render_and_save_pdf(
    html: str,
    output_path: Path,
) -> Path:
    """Render HTML to PDF and write to disk.

    Creates parent directories if they don't exist.

    Returns:
        The output_path for convenience.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pdf_bytes = render_invoice_pdf(html)
    output_path.write_bytes(pdf_bytes)
    logger.info("PDF rendered: %s (%d bytes)", output_path, len(pdf_bytes))
    return output_path
