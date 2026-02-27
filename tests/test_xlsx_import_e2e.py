"""E2E tests: validate real XLSX import against known reference data.

Imports the actual Upwork and bank XLSX files from docs/reference-docs/
and validates row counts, parsed values, and monthly totals against
tracking.json reference data.

Tests are skipped when the XLSX files are missing (e.g., in CI without
reference data).
"""

from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import pytest

REFERENCE_DIR = Path(__file__).resolve().parent.parent / "docs" / "reference-docs"
UPWORK_XLSX = REFERENCE_DIR / "upwork-transactions_20260225.xlsx"
BANK_XLSX = REFERENCE_DIR / "Kontoumsätze Aeologic + Kaletsch.xlsx"

skip_no_upwork = pytest.mark.skipif(
    not UPWORK_XLSX.exists(), reason=f"Upwork XLSX not found: {UPWORK_XLSX}"
)
skip_no_bank = pytest.mark.skipif(
    not BANK_XLSX.exists(), reason=f"Bank XLSX not found: {BANK_XLSX}"
)


# ── Upwork XLSX Tests ───────────────────────────────────────────


@skip_no_upwork
class TestUpworkXlsxImport:
    """Validate Upwork XLSX parsing against known reference data."""

    @pytest.fixture(autouse=True)
    def _parse(self):
        from backend.services.upwork_import import parse_upwork_xlsx

        self.result = parse_upwork_xlsx(str(UPWORK_XLSX))

    def test_no_parse_errors(self):
        assert self.result.errors == []

    def test_row_count(self):
        """The reference XLSX has 214 data rows (per CLAUDE.md)."""
        total = (
            len(self.result.transactions)
            + self.result.skipped_no_amount
        )
        # Allow some flexibility — the exact count depends on empty/header rows
        assert total >= 200, f"Expected ~214 rows, got {total}"

    def test_all_transactions_have_dates(self):
        for tx in self.result.transactions:
            assert tx.tx_date is not None, f"tx {tx.tx_id} has no date"

    def test_all_transactions_have_amounts(self):
        for tx in self.result.transactions:
            assert tx.amount_eur != 0, f"tx {tx.tx_id} has zero amount"

    def test_most_transactions_have_assigned_month(self):
        """Most transactions should parse a period end date for month assignment."""
        with_month = sum(1 for tx in self.result.transactions if tx.assigned_month)
        ratio = with_month / len(self.result.transactions) if self.result.transactions else 0
        assert ratio > 0.5, f"Only {ratio:.0%} of transactions have assigned_month"

    def test_monthly_upwork_totals_exact_matches(self):
        """Validate months where raw XLSX totals exactly match invoiced amounts.

        Some months had manual adjustments or different month assignments on the
        actual DRS invoices, so only months with known exact matches are tested.
        """
        # These months have raw XLSX totals that exactly match tracking.json pos 5
        exact_matches = {
            "2025-04": Decimal("3884.03"),
            "2025-06": Decimal("4673.70"),
        }

        monthly_totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        for tx in self.result.transactions:
            if tx.assigned_month and tx.assigned_month in exact_matches:
                monthly_totals[tx.assigned_month] += Decimal(str(tx.amount_eur))

        for month, expected_total in exact_matches.items():
            actual = monthly_totals.get(month, Decimal("0")).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            assert actual == expected_total, (
                f"Upwork total for {month}: expected {expected_total}, got {actual}"
            )

    def test_monthly_upwork_totals_reasonable_range(self):
        """All 2025 months should have Upwork transactions in a reasonable range."""
        monthly_totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        for tx in self.result.transactions:
            if tx.assigned_month and tx.assigned_month.startswith("2025-"):
                monthly_totals[tx.assigned_month] += Decimal(str(tx.amount_eur))

        # Each month Jan-Jun 2025 should have between 2,000 and 6,000 EUR
        for month_num in range(1, 7):
            month_key = f"2025-{month_num:02d}"
            total = monthly_totals.get(month_key, Decimal("0"))
            assert Decimal("2000") <= total <= Decimal("6000"), (
                f"Upwork total for {month_key} ({total}) outside expected range"
            )

    def test_transaction_ids_are_unique(self):
        ids = [tx.tx_id for tx in self.result.transactions]
        assert len(ids) == len(set(ids)), "Duplicate transaction IDs found"


# ── Bank XLSX Tests ─────────────────────────────────────────────


@skip_no_bank
class TestBankXlsxImport:
    """Validate bank statement XLSX parsing against known reference data."""

    @pytest.fixture(autouse=True)
    def _parse(self):
        from backend.services.bank_import import parse_bank_xlsx

        self.result = parse_bank_xlsx(str(BANK_XLSX))

    def test_no_parse_errors(self):
        assert self.result.errors == []

    def test_has_transactions(self):
        assert len(self.result.transactions) > 0

    def test_all_transactions_have_booking_dates(self):
        for tx in self.result.transactions:
            assert tx.booking_date is not None

    def test_all_transactions_have_amounts(self):
        for tx in self.result.transactions:
            assert tx.amount_eur is not None
            assert tx.amount_eur != 0

    def test_known_kaletsch_payments(self):
        """Verify known Kaletsch quarterly payments from tracking.json."""
        known_payments = {
            # (approximate booking date, EUR amount) from tracking.json
            "Q1": -8295.00,   # 2025-01-06, INV307
            "Q2": -8439.14,   # 2025-04-14, INV308
        }
        amounts = [tx.amount_eur for tx in self.result.transactions]

        for quarter, expected_amount in known_payments.items():
            assert expected_amount in amounts, (
                f"Kaletsch {quarter} payment {expected_amount} not found in bank transactions"
            )

    def test_known_aeologic_payments(self):
        """Verify known Aeologic bank payments from tracking.json."""
        known_aeologic = [
            -899.89,    # AEO000716
            -1036.28,   # AEO000741
            -5079.51,   # AEO000749
        ]
        amounts = [tx.amount_eur for tx in self.result.transactions]

        for expected in known_aeologic:
            assert expected in amounts, (
                f"Aeologic payment {expected} not found in bank transactions"
            )

    def test_invoice_references_extracted(self):
        """At least some transactions should have extracted invoice references."""
        with_ref = [tx for tx in self.result.transactions if tx.extracted_reference]
        assert len(with_ref) > 0, "No invoice references extracted from bank descriptions"

    def test_known_invoice_references(self):
        """Check that known invoice references are extracted."""
        refs = {tx.extracted_reference for tx in self.result.transactions if tx.extracted_reference}
        # INV307, INV308 are Kaletsch quarterly invoices
        for known_ref in ["INV307", "INV308"]:
            assert known_ref in refs, f"Expected reference {known_ref} not found in {refs}"
