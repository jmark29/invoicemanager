"""Bidirectional transaction-to-invoice matching service.

Handles auto-matching after bank imports and invoice creation,
confidence scoring, and FX/fee calculation on match confirmation.
"""

import logging
import re
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy.orm import Session

from backend.models.bank_transaction import BankTransaction
from backend.models.provider_invoice import ProviderInvoice

logger = logging.getLogger(__name__)

# Confidence thresholds
HIGH_CONFIDENCE = 0.95  # auto-link
MEDIUM_CONFIDENCE_MIN = 0.60
LOW_CONFIDENCE = 0.30

# Matching parameters
AMOUNT_TOLERANCE_EUR = 0.01  # 1% for EUR amount matching
DATE_WINDOW_DAYS = 45


@dataclass
class MatchCandidate:
    """A potential match between a bank transaction and a provider invoice."""
    provider_invoice_id: int
    bank_transaction_id: int
    confidence: float
    match_reason: str  # "invoice_number", "amount_date", "category_only"


@dataclass
class MatchStats:
    """Summary of auto-match results."""
    auto_matched: int = 0
    suggested: int = 0
    unmatched: int = 0


def _invoice_number_in_description(invoice_number: str, description: str) -> bool:
    """Check if an invoice number appears in a bank transaction description."""
    desc_lower = description.lower()
    inv_lower = invoice_number.lower()

    # Direct substring match
    if inv_lower in desc_lower:
        return True

    # Handle slash-based numbers like "01/2025" — try with dash too
    if "/" in inv_lower:
        dash_variant = inv_lower.replace("/", "-")
        if dash_variant in desc_lower:
            return True

    # Try extracting references from description and comparing
    from backend.services.bank_import import INVOICE_REF_PATTERNS
    for pattern in INVOICE_REF_PATTERNS:
        m = pattern.search(description)
        if m and m.group(1).lower() == inv_lower:
            return True

    return False


def find_invoice_matches_for_transaction(
    transaction: BankTransaction,
    db: Session,
) -> list[MatchCandidate]:
    """Find potential provider invoice matches for a bank transaction.

    Returns matches sorted by confidence (highest first).
    """
    if transaction.provider_invoice_id is not None:
        return []  # Already linked

    candidates: list[MatchCandidate] = []

    # Get unlinked invoices in the same category (if category known)
    query = db.query(ProviderInvoice).filter(
        ProviderInvoice.payment_status.in_(["unpaid", "partial"]),
    )
    if transaction.category_id:
        query = query.filter(ProviderInvoice.category_id == transaction.category_id)

    unlinked_invoices = query.all()

    for inv in unlinked_invoices:
        confidence = 0.0
        reason = "category_only"

        # High confidence: invoice number in description
        if _invoice_number_in_description(inv.invoice_number, transaction.description):
            confidence = HIGH_CONFIDENCE
            reason = "invoice_number"
        elif transaction.category_id and inv.category_id == transaction.category_id:
            # Medium confidence: amount + date proximity (EUR only)
            amount_match = False
            if inv.currency == "EUR":
                tx_amount = abs(transaction.amount_eur)
                diff = abs(tx_amount - inv.amount)
                tolerance = inv.amount * AMOUNT_TOLERANCE_EUR
                if diff <= max(tolerance, 1.0):  # At least 1 EUR tolerance
                    amount_match = True

            date_match = False
            if transaction.booking_date and inv.invoice_date:
                days_diff = abs((transaction.booking_date - inv.invoice_date).days)
                if days_diff <= DATE_WINDOW_DAYS:
                    date_match = True

            if amount_match and date_match:
                # Closer dates = higher confidence
                days_diff = abs((transaction.booking_date - inv.invoice_date).days)
                date_factor = max(0.0, 1.0 - (days_diff / DATE_WINDOW_DAYS))
                confidence = MEDIUM_CONFIDENCE_MIN + (0.2 * date_factor)
                reason = "amount_date"
            elif amount_match:
                confidence = 0.50
                reason = "amount_date"
            elif transaction.category_id == inv.category_id:
                confidence = LOW_CONFIDENCE
                reason = "category_only"

        if confidence > 0:
            candidates.append(MatchCandidate(
                provider_invoice_id=inv.id,
                bank_transaction_id=transaction.id,
                confidence=confidence,
                match_reason=reason,
            ))

    candidates.sort(key=lambda c: c.confidence, reverse=True)
    return candidates


def find_transaction_matches_for_invoice(
    invoice: ProviderInvoice,
    db: Session,
) -> list[MatchCandidate]:
    """Find potential bank transaction matches for a provider invoice.

    Returns matches sorted by confidence (highest first).
    """
    if invoice.payment_status == "matched":
        return []  # Already matched

    candidates: list[MatchCandidate] = []

    # Get unlinked transactions in the same category
    query = db.query(BankTransaction).filter(
        BankTransaction.provider_invoice_id.is_(None),
        BankTransaction.match_status.in_(["unmatched", "suggested"]),
    )
    if invoice.category_id:
        query = query.filter(BankTransaction.category_id == invoice.category_id)

    unlinked_txns = query.all()

    for tx in unlinked_txns:
        confidence = 0.0
        reason = "category_only"

        # High confidence: invoice number in description
        if _invoice_number_in_description(invoice.invoice_number, tx.description):
            confidence = HIGH_CONFIDENCE
            reason = "invoice_number"
        elif invoice.category_id and tx.category_id == invoice.category_id:
            # Medium confidence: amount + date proximity (EUR only)
            amount_match = False
            if invoice.currency == "EUR":
                tx_amount = abs(tx.amount_eur)
                diff = abs(tx_amount - invoice.amount)
                tolerance = invoice.amount * AMOUNT_TOLERANCE_EUR
                if diff <= max(tolerance, 1.0):
                    amount_match = True

            date_match = False
            if tx.booking_date and invoice.invoice_date:
                days_diff = abs((tx.booking_date - invoice.invoice_date).days)
                if days_diff <= DATE_WINDOW_DAYS:
                    date_match = True

            if amount_match and date_match:
                days_diff = abs((tx.booking_date - invoice.invoice_date).days)
                date_factor = max(0.0, 1.0 - (days_diff / DATE_WINDOW_DAYS))
                confidence = MEDIUM_CONFIDENCE_MIN + (0.2 * date_factor)
                reason = "amount_date"
            elif amount_match:
                confidence = 0.50
                reason = "amount_date"
            elif tx.category_id == invoice.category_id:
                confidence = LOW_CONFIDENCE
                reason = "category_only"

        if confidence > 0:
            candidates.append(MatchCandidate(
                provider_invoice_id=invoice.id,
                bank_transaction_id=tx.id,
                confidence=confidence,
                match_reason=reason,
            ))

    candidates.sort(key=lambda c: c.confidence, reverse=True)
    return candidates


def apply_match(
    bank_transaction_id: int,
    provider_invoice_id: int,
    db: Session,
    match_type: str = "auto_matched",
    bank_fee_override: float | None = None,
) -> dict:
    """Link a bank transaction to a provider invoice and compute FX values.

    Sets both bidirectional FKs, computes amount_eur/fx_rate/bank_fee,
    and updates match/payment status.

    Returns dict with computed values.
    """
    tx = db.get(BankTransaction, bank_transaction_id)
    inv = db.get(ProviderInvoice, provider_invoice_id)

    if not tx or not inv:
        raise ValueError(f"Transaction {bank_transaction_id} or invoice {provider_invoice_id} not found")

    bank_amount = abs(tx.amount_eur)

    # Compute FX values
    if inv.currency == "EUR":
        amount_eur = bank_amount
        fx_rate = 1.0
        bank_fee = round(bank_amount - inv.amount, 2) if bank_amount != inv.amount else 0.0
    else:
        # Foreign currency (USD, ZAR, etc.)
        amount_eur = bank_amount  # Full bank debit = what gets billed to client
        fx_rate = round(bank_amount / inv.amount, 6) if inv.amount else None
        bank_fee = bank_fee_override  # Only known if manually entered

    if bank_fee_override is not None:
        bank_fee = bank_fee_override

    # Update bank transaction
    tx.provider_invoice_id = inv.id
    tx.match_status = match_type
    tx.match_confidence = 1.0 if match_type in ("auto_matched", "manual") else None

    # Update provider invoice (bidirectional)
    inv.matched_transaction_id = tx.id
    inv.payment_status = "matched"
    inv.amount_eur = amount_eur
    inv.fx_rate = fx_rate
    inv.bank_fee = bank_fee

    db.commit()

    logger.info(
        "Matched tx #%d to invoice %s (%s): amount_eur=%.2f, fx_rate=%s",
        tx.id, inv.invoice_number, match_type, amount_eur,
        f"{fx_rate:.6f}" if fx_rate else "N/A",
    )

    return {
        "amount_eur": amount_eur,
        "fx_rate": fx_rate,
        "bank_fee": bank_fee,
        "match_status": match_type,
    }


def reject_match(
    bank_transaction_id: int,
    db: Session,
) -> None:
    """Reject a suggested match — mark the transaction as rejected."""
    tx = db.get(BankTransaction, bank_transaction_id)
    if not tx:
        raise ValueError(f"Transaction {bank_transaction_id} not found")

    tx.match_status = "rejected"
    tx.match_confidence = None
    db.commit()

    logger.info("Rejected suggested match for tx #%d", tx.id)


def auto_match_after_bank_import(
    imported_transaction_ids: list[int],
    db: Session,
) -> MatchStats:
    """Run auto-matching on newly imported bank transactions.

    High confidence matches are auto-linked immediately.
    Medium confidence matches are flagged as 'suggested'.
    """
    stats = MatchStats()

    for tx_id in imported_transaction_ids:
        tx = db.get(BankTransaction, tx_id)
        if not tx or tx.provider_invoice_id is not None:
            continue

        candidates = find_invoice_matches_for_transaction(tx, db)
        if not candidates:
            stats.unmatched += 1
            continue

        best = candidates[0]

        if best.confidence >= HIGH_CONFIDENCE:
            # Auto-link
            apply_match(tx_id, best.provider_invoice_id, db, "auto_matched")
            stats.auto_matched += 1
        elif best.confidence >= MEDIUM_CONFIDENCE_MIN:
            # Suggest but don't auto-link
            tx.match_status = "suggested"
            tx.match_confidence = best.confidence
            db.commit()
            stats.suggested += 1
        else:
            stats.unmatched += 1

    logger.info(
        "Auto-match after bank import: %d auto-matched, %d suggested, %d unmatched",
        stats.auto_matched, stats.suggested, stats.unmatched,
    )
    return stats


def auto_match_after_invoice_creation(
    invoice_id: int,
    db: Session,
) -> MatchCandidate | None:
    """Run auto-matching when a new provider invoice is created.

    If a high-confidence match is found, auto-links immediately.
    Returns the matched candidate or None.
    """
    inv = db.get(ProviderInvoice, invoice_id)
    if not inv or inv.payment_status == "matched":
        return None

    candidates = find_transaction_matches_for_invoice(inv, db)
    if not candidates:
        return None

    best = candidates[0]

    if best.confidence >= HIGH_CONFIDENCE:
        apply_match(best.bank_transaction_id, invoice_id, db, "auto_matched")
        logger.info(
            "Auto-matched new invoice %s to tx #%d (confidence=%.2f)",
            inv.invoice_number, best.bank_transaction_id, best.confidence,
        )
        return best
    elif best.confidence >= MEDIUM_CONFIDENCE_MIN:
        # Flag the transaction as suggested
        tx = db.get(BankTransaction, best.bank_transaction_id)
        if tx:
            tx.match_status = "suggested"
            tx.match_confidence = best.confidence
            db.commit()
        return best

    return None
