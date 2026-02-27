"""Phase 5 tests: seed data loading and historical invoice validation.

Tests that:
1. Seed loader populates database correctly and is idempotent
2. preview_invoice produces reasonable auto-computed values for each month
3. With historical overrides, the system matches exact amounts from tracking.json
"""

from decimal import ROUND_HALF_UP, Decimal

import pytest
from sqlalchemy.orm import Session

from backend.models.bank_transaction import BankTransaction
from backend.models.client import Client
from backend.models.cost_category import CostCategory
from backend.models.line_item_definition import LineItemDefinition
from backend.models.provider_invoice import ProviderInvoice
from backend.models.upwork_transaction import UpworkTransaction
from backend.models.working_days_config import WorkingDaysConfig
from backend.seed.loader import seed_all
from backend.seed.seed_data import (
    AUTO_COMPUTED_NET_TOTALS,
    EXPECTED_INVOICES,
    HISTORICAL_OVERRIDES,
)
from backend.services.cost_calculation import InvoicePreview, resolve_line_items


# ── Fixtures ────────────────────────────────────────────────────


@pytest.fixture
def seeded_db(db_session: Session) -> Session:
    """Seed the test database with all historical data."""
    loaded = seed_all(db_session)
    assert loaded is True
    return db_session


# ── Seed Loader Tests ───────────────────────────────────────────


class TestSeedLoader:
    def test_seed_creates_client(self, seeded_db: Session):
        client = seeded_db.get(Client, "drs")
        assert client is not None
        assert client.name == "DRS Holding AG"
        assert client.client_number == "02"
        assert client.zip_city == "20457 Hamburg"
        assert client.vat_rate == 0.19

    def test_seed_creates_cost_categories(self, seeded_db: Session):
        categories = seeded_db.query(CostCategory).all()
        assert len(categories) == 4

        cat_ids = {c.id for c in categories}
        assert cat_ids == {"junior_fm", "cloud_engineer", "upwork_mobile", "aeologic"}

        # Verify cost types
        for cat in categories:
            if cat.id == "junior_fm":
                assert cat.cost_type == "direct"
                assert cat.currency == "EUR"
            elif cat.id == "cloud_engineer":
                assert cat.cost_type == "distributed"
                assert cat.distribution_method == "working_days"
            elif cat.id == "upwork_mobile":
                assert cat.cost_type == "upwork"
            elif cat.id == "aeologic":
                assert cat.cost_type == "direct"
                assert cat.currency == "USD"

    def test_seed_creates_line_item_definitions(self, seeded_db: Session):
        definitions = (
            seeded_db.query(LineItemDefinition)
            .filter(LineItemDefinition.client_id == "drs")
            .order_by(LineItemDefinition.position)
            .all()
        )
        assert len(definitions) == 7

        # Positions 1-7
        assert [d.position for d in definitions] == [1, 2, 3, 4, 5, 6, 7]

        # Fixed positions
        assert definitions[0].source_type == "fixed"
        assert definitions[0].fixed_amount == 16450.00
        assert definitions[1].source_type == "fixed"
        assert definitions[1].fixed_amount == 8300.00

        # Category-linked positions
        assert definitions[2].source_type == "category"
        assert definitions[2].category_id == "junior_fm"
        assert definitions[3].category_id == "cloud_engineer"
        assert definitions[4].category_id == "upwork_mobile"
        assert definitions[5].category_id == "aeologic"

        # Optional Reisekosten
        assert definitions[6].source_type == "manual"
        assert definitions[6].is_optional is True

    def test_seed_creates_junior_fm_invoices(self, seeded_db: Session):
        invoices = (
            seeded_db.query(ProviderInvoice)
            .filter(ProviderInvoice.category_id == "junior_fm")
            .all()
        )
        assert len(invoices) == 12

        # Check Jan 2025
        jan = next(i for i in invoices if i.assigned_month == "2025-01")
        assert jan.invoice_number == "01/2025"
        assert jan.amount == 1300.0
        assert jan.currency == "EUR"
        assert jan.hours == 26

    def test_seed_creates_kaletsch_invoices_with_bank_transactions(self, seeded_db: Session):
        invoices = (
            seeded_db.query(ProviderInvoice)
            .filter(ProviderInvoice.category_id == "cloud_engineer")
            .all()
        )
        assert len(invoices) == 4

        # Q1 covers Jan-Mar
        q1 = next(i for i in invoices if i.invoice_number == "INV307")
        assert q1.covers_months == ["2025-01", "2025-02", "2025-03"]

        # Q1 has linked bank transaction
        bt = (
            seeded_db.query(BankTransaction)
            .filter(BankTransaction.provider_invoice_id == q1.id)
            .first()
        )
        assert bt is not None
        assert bt.amount_eur == -8295.0

        # Q2 covers Apr-Jun
        q2 = next(i for i in invoices if i.invoice_number == "INV308")
        assert q2.covers_months == ["2025-04", "2025-05", "2025-06"]

    def test_seed_creates_aeologic_invoices(self, seeded_db: Session):
        invoices = (
            seeded_db.query(ProviderInvoice)
            .filter(ProviderInvoice.category_id == "aeologic")
            .all()
        )
        # 13 original (minus 4 that are in DRS mapping) + 6 DRS-mapped = at least 6 with assigned_month
        assigned = [i for i in invoices if i.assigned_month is not None]
        assert len(assigned) == 6

        # Check each DRS month has exactly one assigned invoice
        months = {i.assigned_month for i in assigned}
        assert months == {"2025-01", "2025-02", "2025-03", "2025-04", "2025-05", "2025-06"}

        # Each assigned invoice has a linked bank transaction
        for inv in assigned:
            bt = (
                seeded_db.query(BankTransaction)
                .filter(BankTransaction.provider_invoice_id == inv.id)
                .first()
            )
            assert bt is not None, f"No bank tx for {inv.invoice_number} ({inv.assigned_month})"
            assert bt.amount_eur < 0  # outgoing

    def test_seed_creates_upwork_transactions(self, seeded_db: Session):
        transactions = seeded_db.query(UpworkTransaction).all()
        assert len(transactions) == 6

        # Check each month has a transaction
        for tx in transactions:
            assert tx.assigned_month is not None
            assert tx.category_id == "upwork_mobile"
            assert tx.amount_eur > 0

    def test_seed_creates_working_days_config(self, seeded_db: Session):
        config = seeded_db.query(WorkingDaysConfig).first()
        assert config is not None
        assert config.country == "DE"
        assert config.state == "HE"

    def test_seed_is_idempotent(self, seeded_db: Session):
        """Second call to seed_all should return False and not duplicate data."""
        loaded = seed_all(seeded_db)
        assert loaded is False

        # Still only 1 client
        assert seeded_db.query(Client).count() == 1


# ── Auto-Computed Preview Tests ─────────────────────────────────


class TestAutoComputedPreview:
    """Test that preview_invoice produces correct auto-computed values.

    The auto-computed values differ from historical for Pos 4 (Kaletsch)
    because the algorithm distributes by working days while the original
    manual process used different amounts.
    """

    @pytest.mark.parametrize("year,month,month_key", [
        (2025, 1, "2025-01"),
        (2025, 2, "2025-02"),
        (2025, 3, "2025-03"),
        (2025, 4, "2025-04"),
        (2025, 5, "2025-05"),
        (2025, 6, "2025-06"),
    ])
    def test_preview_returns_7_items(self, seeded_db: Session, year, month, month_key):
        """Each month should resolve all 7 line item definitions."""
        preview = resolve_line_items("drs", year, month, seeded_db)
        assert len(preview.items) == 7
        positions = [item.position for item in preview.items]
        assert positions == [1, 2, 3, 4, 5, 6, 7]

    @pytest.mark.parametrize("year,month,month_key", [
        (2025, 1, "2025-01"),
        (2025, 2, "2025-02"),
        (2025, 3, "2025-03"),
        (2025, 4, "2025-04"),
        (2025, 5, "2025-05"),
        (2025, 6, "2025-06"),
    ])
    def test_fixed_amounts_correct(self, seeded_db: Session, year, month, month_key):
        """Pos 1 and 2 (fixed) should always be 16450.00 and 8300.00."""
        preview = resolve_line_items("drs", year, month, seeded_db)
        assert preview.items[0].amount == 16450.00
        assert preview.items[0].source_type == "fixed"
        assert preview.items[1].amount == 8300.00
        assert preview.items[1].source_type == "fixed"

    @pytest.mark.parametrize("year,month,month_key,expected_amount", [
        (2025, 1, "2025-01", 1300.0),
        (2025, 2, "2025-02", 3800.0),
        (2025, 3, "2025-03", 2000.0),
        (2025, 4, "2025-04", 2000.0),
        (2025, 5, "2025-05", 1600.0),
        (2025, 6, "2025-06", 1800.0),
    ])
    def test_junior_fm_direct_amount(self, seeded_db: Session, year, month, month_key, expected_amount):
        """Pos 3 (Junior FM, direct EUR) should match invoice amounts."""
        preview = resolve_line_items("drs", year, month, seeded_db)
        item = preview.items[2]
        assert item.position == 3
        assert item.source_type == "direct"
        assert item.amount == expected_amount

    @pytest.mark.parametrize("year,month,month_key", [
        (2025, 1, "2025-01"),
        (2025, 2, "2025-02"),
        (2025, 3, "2025-03"),
        (2025, 4, "2025-04"),
        (2025, 5, "2025-05"),
        (2025, 6, "2025-06"),
    ])
    def test_kaletsch_distributed_positive(self, seeded_db: Session, year, month, month_key):
        """Pos 4 (Kaletsch, distributed) should produce a positive amount."""
        preview = resolve_line_items("drs", year, month, seeded_db)
        item = preview.items[3]
        assert item.position == 4
        assert item.source_type == "distributed"
        assert item.amount > 2500.0  # reasonable minimum
        assert item.amount < 3500.0  # reasonable maximum

    @pytest.mark.parametrize("year,month,month_key,expected_amount", [
        (2025, 1, "2025-01", 5083.19),
        (2025, 2, "2025-02", 4200.84),
        (2025, 3, "2025-03", 3843.43),
        (2025, 4, "2025-04", 3884.03),
        (2025, 5, "2025-05", 4145.25),
        (2025, 6, "2025-06", 4673.70),
    ])
    def test_upwork_amount(self, seeded_db: Session, year, month, month_key, expected_amount):
        """Pos 5 (Upwork) should match seeded transaction totals."""
        preview = resolve_line_items("drs", year, month, seeded_db)
        item = preview.items[4]
        assert item.position == 5
        assert item.source_type == "upwork"
        assert item.amount == expected_amount

    @pytest.mark.parametrize("year,month,month_key,expected_amount", [
        (2025, 1, "2025-01", 1551.41),
        (2025, 2, "2025-02", 1036.28),
        (2025, 3, "2025-03", 5079.51),
        (2025, 4, "2025-04", 8238.89),
        (2025, 5, "2025-05", 6122.20),
        (2025, 6, "2025-06", 2512.79),
    ])
    def test_aeologic_direct_usd_amount(self, seeded_db: Session, year, month, month_key, expected_amount):
        """Pos 6 (Aeologic, direct USD) should match bank EUR amounts."""
        preview = resolve_line_items("drs", year, month, seeded_db)
        item = preview.items[5]
        assert item.position == 6
        assert item.source_type == "direct"
        assert item.amount == expected_amount

    @pytest.mark.parametrize("year,month,month_key", [
        (2025, 1, "2025-01"),
        (2025, 2, "2025-02"),
        (2025, 3, "2025-03"),
        (2025, 4, "2025-04"),
        (2025, 5, "2025-05"),
        (2025, 6, "2025-06"),
    ])
    def test_reisekosten_manual_zero(self, seeded_db: Session, year, month, month_key):
        """Pos 7 (Reisekosten, manual) should auto-compute to 0."""
        preview = resolve_line_items("drs", year, month, seeded_db)
        item = preview.items[6]
        assert item.position == 7
        assert item.source_type == "manual"
        assert item.amount == 0.0

    @pytest.mark.parametrize("year,month,month_key", [
        (2025, 1, "2025-01"),
        (2025, 2, "2025-02"),
        (2025, 3, "2025-03"),
        (2025, 4, "2025-04"),
        (2025, 5, "2025-05"),
        (2025, 6, "2025-06"),
    ])
    def test_auto_computed_net_total(self, seeded_db: Session, year, month, month_key):
        """Auto-computed net totals should match expected algorithmic values."""
        preview = resolve_line_items("drs", year, month, seeded_db)
        expected_net = AUTO_COMPUTED_NET_TOTALS[month_key]
        assert preview.net_total == pytest.approx(expected_net, abs=0.01)

    @pytest.mark.parametrize("year,month,month_key", [
        (2025, 1, "2025-01"),
        (2025, 2, "2025-02"),
        (2025, 3, "2025-03"),
        (2025, 4, "2025-04"),
        (2025, 5, "2025-05"),
        (2025, 6, "2025-06"),
    ])
    def test_auto_computed_totals_consistent(self, seeded_db: Session, year, month, month_key):
        """Gross should equal net + VAT for all months."""
        preview = resolve_line_items("drs", year, month, seeded_db)
        assert preview.gross_total == pytest.approx(
            preview.net_total + preview.vat_amount, abs=0.01
        )
        assert preview.vat_amount == pytest.approx(
            preview.net_total * 0.19, abs=0.01
        )


# ── Historical Validation Tests (with overrides) ────────────────


def _apply_overrides(preview: InvoicePreview, overrides: dict[int, float]) -> tuple[float, float, float]:
    """Apply amount overrides to preview items and recalculate totals.

    Mimics the override logic in generate_invoice but without PDF rendering.
    Returns (net_total, vat_amount, gross_total).
    """
    for item in preview.items:
        if item.position in overrides:
            item.amount = overrides[item.position]

    net = sum((Decimal(str(item.amount)) for item in preview.items), Decimal("0"))
    net_rounded = net.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    vat = (net_rounded * Decimal("0.19")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    gross = net_rounded + vat

    return float(net_rounded), float(vat), float(gross)


class TestHistoricalValidation:
    """Validate that with overrides, the system produces exact historical totals.

    The overrides correct for Pos 4 (Kaletsch) algorithmic distribution differences
    and Pos 7 (Reisekosten) manual entry (Feb 2025 only).
    """

    @pytest.mark.parametrize("year,month,month_key", [
        (2025, 1, "2025-01"),
        (2025, 2, "2025-02"),
        (2025, 3, "2025-03"),
        (2025, 4, "2025-04"),
        (2025, 5, "2025-05"),
        (2025, 6, "2025-06"),
    ])
    def test_historical_net_total(self, seeded_db: Session, year, month, month_key):
        """Net total with overrides matches tracking.json."""
        preview = resolve_line_items("drs", year, month, seeded_db)
        overrides = HISTORICAL_OVERRIDES[month_key]
        net, _vat, _gross = _apply_overrides(preview, overrides)

        expected = EXPECTED_INVOICES[month_key]
        assert net == expected["net_total"]

    @pytest.mark.parametrize("year,month,month_key", [
        (2025, 1, "2025-01"),
        (2025, 2, "2025-02"),
        (2025, 3, "2025-03"),
        (2025, 4, "2025-04"),
        (2025, 5, "2025-05"),
        (2025, 6, "2025-06"),
    ])
    def test_historical_vat_amount(self, seeded_db: Session, year, month, month_key):
        """VAT amount with overrides matches tracking.json."""
        preview = resolve_line_items("drs", year, month, seeded_db)
        overrides = HISTORICAL_OVERRIDES[month_key]
        _net, vat, _gross = _apply_overrides(preview, overrides)

        expected = EXPECTED_INVOICES[month_key]
        assert vat == expected["vat_amount"]

    @pytest.mark.parametrize("year,month,month_key", [
        (2025, 1, "2025-01"),
        (2025, 2, "2025-02"),
        (2025, 3, "2025-03"),
        (2025, 4, "2025-04"),
        (2025, 5, "2025-05"),
        (2025, 6, "2025-06"),
    ])
    def test_historical_gross_total(self, seeded_db: Session, year, month, month_key):
        """Gross total with overrides matches tracking.json."""
        preview = resolve_line_items("drs", year, month, seeded_db)
        overrides = HISTORICAL_OVERRIDES[month_key]
        _net, _vat, gross = _apply_overrides(preview, overrides)

        expected = EXPECTED_INVOICES[month_key]
        assert gross == expected["gross_total"]

    @pytest.mark.parametrize("year,month,month_key", [
        (2025, 1, "2025-01"),
        (2025, 2, "2025-02"),
        (2025, 3, "2025-03"),
        (2025, 4, "2025-04"),
        (2025, 5, "2025-05"),
        (2025, 6, "2025-06"),
    ])
    def test_historical_line_item_amounts(self, seeded_db: Session, year, month, month_key):
        """Each line item matches the historical amount after overrides."""
        preview = resolve_line_items("drs", year, month, seeded_db)
        overrides = HISTORICAL_OVERRIDES[month_key]

        expected_items = EXPECTED_INVOICES[month_key]["line_items"]
        for item in preview.items:
            if item.position in overrides:
                item.amount = overrides[item.position]

            if item.position in expected_items:
                assert item.amount == pytest.approx(
                    expected_items[item.position], abs=0.01
                ), f"Month {month_key} Pos {item.position}: {item.amount} != {expected_items[item.position]}"
