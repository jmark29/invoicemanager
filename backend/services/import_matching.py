"""Import matching service — matches extracted line items to definitions and provider invoices.

Used during invoice import to auto-populate line_item_config_id, source_type,
category_id, and to create InvoiceLineItemSource links.
"""

from dataclasses import dataclass, field

from sqlalchemy import and_
from sqlalchemy.orm import Session

from backend.models.cost_category import CostCategory
from backend.models.line_item_definition import LineItemDefinition
from backend.models.provider_invoice import ProviderInvoice
from backend.services.docx_extraction import ExtractedLineItem


@dataclass
class LinkedProviderInvoice:
    provider_invoice_id: int
    invoice_number: str
    amount_contributed: float


@dataclass
class MatchedLineItem:
    position: int
    description: str
    amount: float
    line_item_config_id: int | None = None
    source_type: str | None = None
    category_id: str | None = None
    linked_provider_invoices: list[LinkedProviderInvoice] = field(default_factory=list)
    match_confidence: str = "none"  # high, medium, none


def _normalize(text: str) -> str:
    """Normalize text for comparison: lowercase, collapse whitespace, strip punctuation."""
    import re

    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    # Remove trailing punctuation
    text = text.rstrip(".,;:")
    return text


def match_line_items_to_definitions(
    extracted_items: list[ExtractedLineItem],
    client_id: str,
    db: Session,
) -> list[MatchedLineItem]:
    """Match extracted line item descriptions to LineItemDefinition records.

    Uses position-based matching first (exact position match), then falls back
    to description similarity. Returns MatchedLineItem with config links populated.
    """
    definitions = (
        db.query(LineItemDefinition)
        .filter(LineItemDefinition.client_id == client_id)
        .order_by(LineItemDefinition.position)
        .all()
    )

    # Build lookup maps
    by_position: dict[int, LineItemDefinition] = {d.position: d for d in definitions}
    by_label_normalized: dict[str, LineItemDefinition] = {
        _normalize(d.label): d for d in definitions
    }

    results: list[MatchedLineItem] = []

    for item in extracted_items:
        matched = MatchedLineItem(
            position=item.position,
            description=item.description,
            amount=item.amount,
        )

        # Strategy 1: exact position match + description check
        defn = by_position.get(item.position)
        if defn:
            norm_extracted = _normalize(item.description)
            norm_label = _normalize(defn.label)
            # Check if descriptions are similar (one contains the other)
            if norm_extracted == norm_label or norm_label in norm_extracted or norm_extracted in norm_label:
                matched.line_item_config_id = defn.id
                matched.source_type = defn.source_type
                matched.category_id = defn.category_id
                matched.match_confidence = "high"
                results.append(matched)
                continue

        # Strategy 2: fuzzy description match across all definitions
        norm_extracted = _normalize(item.description)
        best_match = None
        for norm_label, defn in by_label_normalized.items():
            if norm_label in norm_extracted or norm_extracted in norm_label:
                best_match = defn
                break

        if best_match:
            matched.line_item_config_id = best_match.id
            matched.source_type = best_match.source_type
            matched.category_id = best_match.category_id
            matched.match_confidence = "medium"
        else:
            # Strategy 3: position match without description check
            if defn:
                matched.line_item_config_id = defn.id
                matched.source_type = defn.source_type
                matched.category_id = defn.category_id
                matched.match_confidence = "medium"

        results.append(matched)

    return results


def auto_link_to_provider_invoices(
    matched_items: list[MatchedLineItem],
    period_year: int,
    period_month: int,
    db: Session,
) -> list[MatchedLineItem]:
    """For category-based items, find and link provider invoices for the period.

    Looks up provider invoices by category_id and month (via assigned_month
    or covers_months). Updates linked_provider_invoices on each matched item.
    """
    month_str = f"{period_year}-{period_month:02d}"

    for item in matched_items:
        if not item.category_id or item.source_type not in ("category",):
            continue

        category = db.get(CostCategory, item.category_id)
        if not category:
            continue

        if category.cost_type == "direct":
            # Find provider invoices for this category + month
            invoices = (
                db.query(ProviderInvoice)
                .filter(
                    and_(
                        ProviderInvoice.category_id == item.category_id,
                        ProviderInvoice.assigned_month == month_str,
                    )
                )
                .all()
            )
            for inv in invoices:
                amount = inv.amount_eur if inv.amount_eur is not None else inv.amount
                item.linked_provider_invoices.append(
                    LinkedProviderInvoice(
                        provider_invoice_id=inv.id,
                        invoice_number=inv.invoice_number,
                        amount_contributed=amount,
                    )
                )

        elif category.cost_type == "distributed":
            # Find provider invoices whose covers_months includes this month
            all_invoices = (
                db.query(ProviderInvoice)
                .filter(ProviderInvoice.category_id == item.category_id)
                .all()
            )
            for inv in all_invoices:
                if month_str in inv.covers_months:
                    amount = inv.amount_eur if inv.amount_eur is not None else inv.amount
                    item.linked_provider_invoices.append(
                        LinkedProviderInvoice(
                            provider_invoice_id=inv.id,
                            invoice_number=inv.invoice_number,
                            amount_contributed=item.amount,  # use the invoiced amount for this month
                        )
                    )

        elif category.cost_type == "upwork":
            # Upwork transactions are handled differently (via upwork_tx_ids_json)
            # No provider invoice linking needed here
            pass

    return matched_items
