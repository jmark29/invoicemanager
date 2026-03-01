"""PDF text extraction service for bulk provider invoice upload.

Extracts invoice metadata (number, date, amount, currency) from PDF files
using pdfplumber. Each known provider has specific regex patterns for parsing.
Falls back gracefully if text extraction fails (scanned PDFs, unusual formats).
"""

import logging
import re
from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy.orm import Session

from backend.models.cost_category import CostCategory

logger = logging.getLogger(__name__)


@dataclass
class ExtractedInvoiceData:
    """Metadata extracted from a single PDF."""
    filename: str
    invoice_number: str | None = None
    invoice_date: date | None = None
    amount: float | None = None
    currency: str | None = None
    category_id: str | None = None
    confidence: str = "low"  # "high", "medium", "low"
    raw_text: str = ""
    stored_path: str = ""


# ── Provider-specific extraction patterns ──────────────────────────────

def _extract_aeologic(text: str) -> dict:
    """Extract metadata from Aeologic invoice PDFs (USD)."""
    result: dict = {"currency": "USD"}

    # Invoice number: "Invoice #: AEO000852" or "Invoice # AEO000852"
    m = re.search(r"Invoice\s*#\s*:?\s*(AEO\d+)", text, re.IGNORECASE)
    if m:
        result["invoice_number"] = m.group(1)

    # Date: "DD/MM/YYYY" or "Month DD, YYYY" or "DD Month YYYY"
    for pattern, fmt in [
        (r"(\d{2}/\d{2}/\d{4})", "%d/%m/%Y"),
        (r"(\d{2}\.\d{2}\.\d{4})", "%d.%m.%Y"),
    ]:
        m = re.search(pattern, text)
        if m:
            try:
                result["invoice_date"] = datetime.strptime(m.group(1), fmt).date()
                break
            except ValueError:
                continue

    # Try "Month DD, YYYY" format
    if "invoice_date" not in result:
        months = {
            "january": 1, "february": 2, "march": 3, "april": 4,
            "may": 5, "june": 6, "july": 7, "august": 8,
            "september": 9, "october": 10, "november": 11, "december": 12,
        }
        m = re.search(
            r"(\w+)\s+(\d{1,2}),?\s+(\d{4})", text, re.IGNORECASE
        )
        if m and m.group(1).lower() in months:
            try:
                result["invoice_date"] = date(
                    int(m.group(3)), months[m.group(1).lower()], int(m.group(2))
                )
            except ValueError:
                pass

    # Amount: look for "Total Due" or "Amount Due" followed by a number
    for pattern in [
        r"(?:Total\s*Due|Amount\s*Due|Balance\s*Due)\s*:?\s*\$?\s*([\d,]+\.?\d*)",
        r"(?:Total|Grand\s*Total)\s*:?\s*\$?\s*([\d,]+\.?\d*)",
    ]:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            amount_str = m.group(1).replace(",", "")
            try:
                result["amount"] = float(amount_str)
                break
            except ValueError:
                continue

    return result


def _extract_junior_fm(text: str) -> dict:
    """Extract metadata from Junior FM (Iakovlev) invoice PDFs (EUR)."""
    result: dict = {"currency": "EUR"}

    # Invoice number: "01/2025" or "12/2025" pattern
    m = re.search(r"(\d{2}/\d{4})", text)
    if m:
        result["invoice_number"] = m.group(1)

    # Date: DD.MM.YYYY
    dates = re.findall(r"(\d{2}\.\d{2}\.\d{4})", text)
    if dates:
        # Usually the invoice date is the first or last date found
        for d in dates:
            try:
                result["invoice_date"] = datetime.strptime(d, "%d.%m.%Y").date()
                break
            except ValueError:
                continue

    # Amount: look for Summe/Total/Gesamt + EUR amount
    for pattern in [
        r"(?:Summe|Gesamtbetrag|Total|Endbetrag|Rechnungsbetrag)\s*:?\s*([\d.,]+)\s*(?:€|EUR)?",
        r"([\d.,]+)\s*(?:€|EUR)\s*$",
    ]:
        m = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if m:
            amount_str = m.group(1).replace(".", "").replace(",", ".")
            try:
                result["amount"] = float(amount_str)
                break
            except ValueError:
                continue

    return result


def _extract_kaletsch(text: str) -> dict:
    """Extract metadata from Kaletsch (Cloud Engineer) invoice PDFs (EUR)."""
    result: dict = {"currency": "EUR"}

    # Invoice number: "INV307", "INV320" etc.
    m = re.search(r"(INV\d+)", text, re.IGNORECASE)
    if m:
        result["invoice_number"] = m.group(1).upper()

    # Date: various formats
    for pattern, fmt in [
        (r"(\d{2}/\d{2}/\d{4})", "%d/%m/%Y"),
        (r"(\d{2}\.\d{2}\.\d{4})", "%d.%m.%Y"),
        (r"(\d{4}-\d{2}-\d{2})", "%Y-%m-%d"),
    ]:
        m = re.search(pattern, text)
        if m:
            try:
                result["invoice_date"] = datetime.strptime(m.group(1), fmt).date()
                break
            except ValueError:
                continue

    # Amount: look for total amounts
    for pattern in [
        r"(?:Total|Amount\s*Due|Grand\s*Total)\s*:?\s*(?:€|EUR|R)?\s*([\d,. ]+)",
        r"(?:€|EUR)\s*([\d,.]+)",
    ]:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            # Handle both German (1.234,56) and English (1,234.56) formats
            amount_str = m.group(1).strip()
            # Try German format first
            if "," in amount_str and "." in amount_str:
                if amount_str.rindex(",") > amount_str.rindex("."):
                    amount_str = amount_str.replace(".", "").replace(",", ".")
                else:
                    amount_str = amount_str.replace(",", "")
            elif "," in amount_str:
                amount_str = amount_str.replace(",", ".")
            try:
                result["amount"] = float(amount_str)
                break
            except ValueError:
                continue

    return result


# ── Generic extraction ─────────────────────────────────────────────────

def _match_category_from_text(
    text: str,
    categories: list[CostCategory],
) -> str | None:
    """Try to match extracted text to a cost category via bank_keywords."""
    text_lower = text.lower()
    for cat in categories:
        for keyword in cat.bank_keywords:
            if keyword.lower() in text_lower:
                return cat.id
    return None


def extract_invoice_data(
    pdf_path: str,
    filename: str,
    categories: list[CostCategory],
    preset_category_id: str | None = None,
) -> ExtractedInvoiceData:
    """Extract invoice metadata from a single PDF file.

    Args:
        pdf_path: Path to the PDF file on disk.
        filename: Original filename of the uploaded PDF.
        categories: List of cost categories for keyword matching.
        preset_category_id: If set, skip category detection and use this.

    Returns:
        ExtractedInvoiceData with extracted fields (None for any field that
        couldn't be parsed).
    """
    result = ExtractedInvoiceData(filename=filename, stored_path=pdf_path)

    # Try to extract text
    try:
        import pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            pages_text = []
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    pages_text.append(text)
            full_text = "\n".join(pages_text)
    except Exception as e:
        logger.warning("Failed to extract text from %s: %s", filename, e)
        full_text = ""

    result.raw_text = full_text

    if not full_text.strip():
        logger.info("No text extracted from %s (possibly scanned)", filename)
        return result

    # Determine category
    if preset_category_id:
        result.category_id = preset_category_id
    else:
        result.category_id = _match_category_from_text(full_text, categories)

    # Also try to detect category from filename
    if not result.category_id:
        filename_lower = filename.lower()
        if "aeo" in filename_lower:
            result.category_id = "aeologic"
        elif "inv" in filename_lower:
            result.category_id = "cloud_engineer"
        elif "er" in filename_lower and any(c.id == "junior_fm" for c in categories):
            result.category_id = "junior_fm"

    # Apply provider-specific extraction
    extracted: dict = {}
    if result.category_id == "aeologic":
        extracted = _extract_aeologic(full_text)
    elif result.category_id == "junior_fm":
        extracted = _extract_junior_fm(full_text)
    elif result.category_id == "cloud_engineer":
        extracted = _extract_kaletsch(full_text)
    else:
        # Try all patterns and pick the best
        for extractor in [_extract_aeologic, _extract_junior_fm, _extract_kaletsch]:
            extracted = extractor(full_text)
            if extracted.get("invoice_number"):
                break

    result.invoice_number = extracted.get("invoice_number")
    result.invoice_date = extracted.get("invoice_date")
    result.amount = extracted.get("amount")
    result.currency = extracted.get("currency")

    # Determine confidence
    fields_found = sum(1 for v in [result.invoice_number, result.invoice_date, result.amount] if v is not None)
    if fields_found >= 3 and result.category_id:
        result.confidence = "high"
    elif fields_found >= 2:
        result.confidence = "medium"
    elif fields_found >= 1:
        result.confidence = "low"
    else:
        result.confidence = "low"

    return result
