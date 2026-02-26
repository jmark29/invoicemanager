"""Phase 2 tests: working days, formatting, and cost calculation."""

from datetime import date
from decimal import Decimal

import pytest

from backend.models.bank_transaction import BankTransaction
from backend.models.client import Client
from backend.models.cost_category import CostCategory
from backend.models.line_item_definition import LineItemDefinition
from backend.models.provider_invoice import ProviderInvoice
from backend.models.upwork_transaction import UpworkTransaction
from backend.services.cost_calculation import (
    InvoicePreview,
    calculate_direct_amount,
    calculate_distributed_amount,
    calculate_fixed_amount,
    calculate_upwork_amount,
    resolve_line_items,
)
from backend.services.formatting import (
    format_date_german,
    format_eur,
    format_month_year,
    format_period,
    invoice_filename,
    invoice_number,
    round_currency,
)
from backend.services.working_days import (
    distribute_cost_by_working_days,
    easter_date,
    hessen_holidays,
    working_days_in_month,
)


# ── Working Days ─────────────────────────────────────────────────────


class TestEasterDate:
    """Verify the Anonymous Gregorian Easter algorithm."""

    @pytest.mark.parametrize(
        "year, expected",
        [
            (2025, date(2025, 4, 20)),
            (2026, date(2026, 4, 5)),
            (2027, date(2027, 3, 28)),
            (2028, date(2028, 4, 16)),
            (2029, date(2029, 4, 1)),
            (2030, date(2030, 4, 21)),
        ],
    )
    def test_easter_dates(self, year, expected):
        assert easter_date(year) == expected


class TestHessenHolidays:
    def test_2025_holiday_count(self):
        holidays = hessen_holidays(2025)
        assert len(holidays) == 10

    def test_2025_includes_fronleichnam(self):
        holidays = hessen_holidays(2025)
        # Easter 2025 = Apr 20, Fronleichnam = Easter + 60 = Jun 19
        assert date(2025, 6, 19) in holidays

    def test_2025_includes_karfreitag(self):
        holidays = hessen_holidays(2025)
        # Karfreitag = Easter - 2 = Apr 18
        assert date(2025, 4, 18) in holidays

    def test_2025_fixed_holidays(self):
        holidays = hessen_holidays(2025)
        assert date(2025, 1, 1) in holidays    # Neujahr
        assert date(2025, 5, 1) in holidays    # Tag der Arbeit
        assert date(2025, 10, 3) in holidays   # Tag der Deutschen Einheit
        assert date(2025, 12, 25) in holidays  # 1. Weihnachtstag
        assert date(2025, 12, 26) in holidays  # 2. Weihnachtstag


class TestWorkingDays:
    """Working days for 2025, cross-checked with the reference implementation."""

    @pytest.mark.parametrize(
        "year, month, expected",
        [
            # 2025 working days for Hessen
            (2025, 1, 22),   # 23 weekdays - 1 holiday (Jan 1)
            (2025, 2, 20),   # 20 weekdays, no holidays
            (2025, 3, 21),   # 21 weekdays, no holidays
            (2025, 4, 20),   # 22 weekdays - 2 holidays (Karfreitag, Ostermontag)
            (2025, 5, 20),   # 22 weekdays - 2 holidays (Tag der Arbeit, Himmelfahrt)
            (2025, 6, 19),   # 21 weekdays - 2 holidays (Pfingstmontag, Fronleichnam)
            (2025, 7, 23),   # 23 weekdays, no holidays
            (2025, 8, 21),   # 21 weekdays, no holidays
            (2025, 9, 22),   # 22 weekdays, no holidays
            (2025, 10, 22),  # 23 weekdays - 1 holiday (Tag der Dt. Einheit)
            (2025, 11, 20),  # 20 weekdays, no holidays
            (2025, 12, 21),  # 23 weekdays - 2 holidays (25., 26.)
        ],
    )
    def test_2025_working_days(self, year, month, expected):
        assert working_days_in_month(year, month) == expected

    def test_2025_annual_total(self):
        total = sum(working_days_in_month(2025, m) for m in range(1, 13))
        assert total == 251  # Standard for Hessen 2025


class TestCostDistribution:
    """Test proportional distribution of costs across months by working days."""

    def test_q1_2025_kaletsch(self):
        """Distribute Kaletsch Q1 bank payment (€8,295.00) across Jan-Mar 2025."""
        dist = distribute_cost_by_working_days(8295.00, [(2025, 1), (2025, 2), (2025, 3)])

        # Working days: Jan=22, Feb=20, Mar=21, Total=63
        # Jan: round(8295 * 22/63, 2) = 2896.67
        # Feb: round(8295 * 20/63, 2) = 2633.33
        # Mar: remainder = 8295 - 2896.67 - 2633.33 = 2765.00
        assert dist[(2025, 1)] == pytest.approx(2896.67, abs=0.01)
        assert dist[(2025, 2)] == pytest.approx(2633.33, abs=0.01)
        assert dist[(2025, 3)] == pytest.approx(2765.00, abs=0.01)

        # Sum must equal total exactly
        total = sum(dist.values())
        assert total == pytest.approx(8295.00, abs=0.001)

    def test_q2_2025_kaletsch(self):
        """Distribute Kaletsch Q2 bank payment (€8,439.14) across Apr-Jun 2025."""
        dist = distribute_cost_by_working_days(8439.14, [(2025, 4), (2025, 5), (2025, 6)])

        # Working days: Apr=20, May=20, Jun=19, Total=59
        total = sum(dist.values())
        assert total == pytest.approx(8439.14, abs=0.001)

    def test_sum_always_equals_total(self):
        """Distribution must always sum exactly to the original total."""
        for total in [1000.00, 8295.00, 9387.36, 12345.67]:
            dist = distribute_cost_by_working_days(total, [(2025, 1), (2025, 2), (2025, 3)])
            assert sum(dist.values()) == pytest.approx(total, abs=0.001)

    def test_single_month(self):
        """Single-month distribution returns the full amount."""
        dist = distribute_cost_by_working_days(5000.0, [(2025, 6)])
        assert dist[(2025, 6)] == 5000.0

    def test_empty_months_raises(self):
        with pytest.raises(ValueError, match="No months"):
            distribute_cost_by_working_days(1000.0, [])


# ── Formatting ───────────────────────────────────────────────────────


class TestFormatEur:
    @pytest.mark.parametrize(
        "amount, expected",
        [
            (1300.0, "1.300,00 \u20ac"),
            (35535.80, "35.535,80 \u20ac"),
            (42287.60, "42.287,60 \u20ac"),
            (0.0, "0,00 \u20ac"),
            (999.999, "1.000,00 \u20ac"),       # rounds up
            (1234567.89, "1.234.567,89 \u20ac"),
            (50.0, "50,00 \u20ac"),
            (-1500.00, "-1.500,00 \u20ac"),
        ],
    )
    def test_format_eur(self, amount, expected):
        assert format_eur(amount) == expected


class TestRoundCurrency:
    def test_rounds_half_up(self):
        assert round_currency(2.555) == Decimal("2.56")
        assert round_currency(2.545) == Decimal("2.55")
        assert round_currency(2.5451) == Decimal("2.55")

    def test_exact_two_decimals(self):
        assert round_currency(100.0) == Decimal("100.00")


class TestDateFormatting:
    def test_format_date_german(self):
        assert format_date_german(date(2025, 2, 28)) == "28.02.2025"
        assert format_date_german(date(2025, 1, 1)) == "01.01.2025"

    def test_format_period(self):
        assert format_period(2025, 1) == "01.01.2025 bis 31.01.2025"
        assert format_period(2025, 2) == "01.02.2025 bis 28.02.2025"
        assert format_period(2024, 2) == "01.02.2024 bis 29.02.2024"  # leap year

    def test_format_month_year(self):
        assert format_month_year(2025, 1) == "Januar 2025"
        assert format_month_year(2025, 12) == "Dezember 2025"


class TestInvoiceNumbering:
    def test_invoice_number(self):
        assert invoice_number(2025, 1, "02") == "202501-02"
        assert invoice_number(2025, 12, "02") == "202512-02"

    def test_invoice_filename(self):
        assert invoice_filename(2025, 1, "02") == "AR202501-02.pdf"
        assert invoice_filename(2025, 6, "02") == "AR202506-02.pdf"


# ── Cost Calculation (with DB) ──────────────────────────────────────


def _seed_basic_data(db):
    """Seed the minimum data needed for cost calculation tests."""
    client = Client(
        id="drs",
        client_number="02",
        name="DRS Holding AG",
        address_line1="Am Sandtorkai 58",
        zip_city="20457 Hamburg",
        vat_rate=0.19,
    )

    # Categories
    cat_pm = CostCategory(
        id="senior_fm", name="Senior FM Developer",
        billing_cycle="monthly", cost_type="fixed", sort_order=1,
    )
    cat_consultant = CostCategory(
        id="senior_consultant", name="Senior Consultant",
        billing_cycle="monthly", cost_type="fixed", sort_order=2,
    )
    cat_junior = CostCategory(
        id="junior_fm", name="Junior FM Developer",
        billing_cycle="monthly", cost_type="direct", currency="EUR", sort_order=3,
    )
    cat_cloud = CostCategory(
        id="cloud_engineer", name="Cloud Engineer",
        billing_cycle="quarterly", cost_type="distributed",
        distribution_method="working_days", sort_order=4,
    )
    cat_cloud.bank_keywords = ["KALETSCH", "RORY KALETSCH"]
    cat_upwork = CostCategory(
        id="mobile_dev", name="Mobile Developer",
        billing_cycle="weekly", cost_type="upwork", sort_order=5,
    )
    cat_aeologic = CostCategory(
        id="aeologic", name="Aeologic Developer",
        billing_cycle="irregular", cost_type="direct", currency="USD", sort_order=6,
    )

    db.add_all([client, cat_pm, cat_consultant, cat_junior, cat_cloud, cat_upwork, cat_aeologic])
    db.flush()

    # Line item definitions
    defs = [
        LineItemDefinition(
            client_id="drs", position=1, label="Senior FileMaker Entwickler",
            source_type="fixed", fixed_amount=16450.0, sort_order=1,
        ),
        LineItemDefinition(
            client_id="drs", position=2, label="Senior Consultant / Projektmanagement",
            source_type="fixed", fixed_amount=8300.0, sort_order=2,
        ),
        LineItemDefinition(
            client_id="drs", position=3, label="Junior FileMaker Entwickler",
            source_type="category", category_id="junior_fm", sort_order=3,
        ),
        LineItemDefinition(
            client_id="drs", position=4, label="Cloud Engineer",
            source_type="category", category_id="cloud_engineer", sort_order=4,
        ),
        LineItemDefinition(
            client_id="drs", position=5, label="Mobile App Entwickler (Upwork)",
            source_type="category", category_id="mobile_dev", sort_order=5,
        ),
        LineItemDefinition(
            client_id="drs", position=6, label="App-Entwickler (Aeologic)",
            source_type="category", category_id="aeologic", sort_order=6,
        ),
    ]
    db.add_all(defs)
    db.flush()

    return client


def _seed_jan_2025_data(db):
    """Seed provider invoices, bank transactions, and Upwork data for Jan 2025."""
    _seed_basic_data(db)

    # Junior FM invoice for Jan 2025
    junior_inv = ProviderInvoice(
        category_id="junior_fm",
        invoice_number="01/2025",
        invoice_date=date(2025, 1, 31),
        amount=1300.0,
        currency="EUR",
        assigned_month="2025-01",
    )
    db.add(junior_inv)
    db.flush()

    # Kaletsch Q1 invoice (distributed across Jan-Mar)
    kaletsch_inv = ProviderInvoice(
        category_id="cloud_engineer",
        invoice_number="INV307",
        invoice_date=date(2025, 3, 1),
        amount=8280.0,
        currency="EUR",
    )
    kaletsch_inv.covers_months = ["2025-01", "2025-02", "2025-03"]
    db.add(kaletsch_inv)
    db.flush()

    # Bank transaction for Kaletsch Q1
    kaletsch_bank = BankTransaction(
        booking_date=date(2025, 1, 6),
        description="KALETSCH INV307",
        amount_eur=-8295.0,  # negative = outgoing payment
        category_id="cloud_engineer",
        provider_invoice_id=kaletsch_inv.id,
        bank_fee=15.0,
    )
    db.add(kaletsch_bank)

    # Aeologic invoice for Jan 2025 (USD, with bank payment)
    aeo_inv = ProviderInvoice(
        category_id="aeologic",
        invoice_number="AEO000716",
        invoice_date=date(2024, 12, 15),
        amount=900.0,
        currency="USD",
        assigned_month="2025-01",
    )
    db.add(aeo_inv)
    db.flush()

    aeo_bank = BankTransaction(
        booking_date=date(2025, 1, 6),
        description="INVOICE  AEO000716",
        amount_eur=-899.89,
        category_id="aeologic",
        provider_invoice_id=aeo_inv.id,
    )
    db.add(aeo_bank)

    # Upwork transactions for Jan 2025
    upwork_txns = [
        UpworkTransaction(
            tx_id="UPW001", tx_date=date(2025, 1, 10),
            description="Invoice for Jan 6-Jan 12, 2025",
            period_start=date(2025, 1, 6), period_end=date(2025, 1, 12),
            amount_eur=1200.50, assigned_month="2025-01",
        ),
        UpworkTransaction(
            tx_id="UPW002", tx_date=date(2025, 1, 17),
            description="Invoice for Jan 13-Jan 19, 2025",
            period_start=date(2025, 1, 13), period_end=date(2025, 1, 19),
            amount_eur=1500.75, assigned_month="2025-01",
        ),
        UpworkTransaction(
            tx_id="UPW003", tx_date=date(2025, 1, 24),
            description="Invoice for Jan 20-Jan 26, 2025",
            period_start=date(2025, 1, 20), period_end=date(2025, 1, 26),
            amount_eur=1100.00, assigned_month="2025-01",
        ),
    ]
    db.add_all(upwork_txns)
    db.flush()


class TestFixedAmount:
    def test_returns_fixed_amount(self):
        defn = LineItemDefinition(
            client_id="drs", position=1, label="Test",
            source_type="fixed", fixed_amount=16450.0, sort_order=1,
        )
        result = calculate_fixed_amount(defn)
        assert result.amount == 16450.0
        assert result.source_type == "fixed"
        assert result.warnings == []

    def test_warns_when_no_amount(self):
        defn = LineItemDefinition(
            client_id="drs", position=1, label="Test",
            source_type="fixed", sort_order=1,
        )
        result = calculate_fixed_amount(defn)
        assert result.amount == 0.0
        assert len(result.warnings) == 1


class TestDirectAmount:
    def test_eur_provider(self, db_session):
        _seed_jan_2025_data(db_session)
        db_session.commit()

        defn = db_session.query(LineItemDefinition).filter_by(position=3).first()
        result = calculate_direct_amount(defn, 2025, 1, db_session)
        assert result.amount == 1300.0
        assert result.source_type == "direct"
        assert result.warnings == []

    def test_usd_provider_uses_bank_eur(self, db_session):
        _seed_jan_2025_data(db_session)
        db_session.commit()

        defn = db_session.query(LineItemDefinition).filter_by(position=6).first()
        result = calculate_direct_amount(defn, 2025, 1, db_session)
        # Should use abs(bank_transaction.amount_eur) = 899.89
        assert result.amount == 899.89
        assert result.warnings == []

    def test_missing_invoice_warns(self, db_session):
        _seed_basic_data(db_session)
        db_session.commit()

        defn = db_session.query(LineItemDefinition).filter_by(position=3).first()
        result = calculate_direct_amount(defn, 2025, 7, db_session)
        assert result.amount == 0.0
        assert len(result.warnings) == 1
        assert "no provider invoice" in result.warnings[0]


class TestDistributedAmount:
    def test_q1_jan_2025(self, db_session):
        _seed_jan_2025_data(db_session)
        db_session.commit()

        defn = db_session.query(LineItemDefinition).filter_by(position=4).first()
        result = calculate_distributed_amount(defn, 2025, 1, db_session)

        # Working days: Jan=22, Feb=20, Mar=21, Total=63
        # Jan share: round(8295 * 22/63, 2)
        expected = float(
            (Decimal("8295") * Decimal("22") / Decimal("63")).quantize(
                Decimal("0.01")
            )
        )
        assert result.amount == pytest.approx(expected, abs=0.01)
        assert result.source_type == "distributed"

    def test_q1_sum_equals_bank_payment(self, db_session):
        _seed_jan_2025_data(db_session)
        db_session.commit()

        defn = db_session.query(LineItemDefinition).filter_by(position=4).first()
        total = 0.0
        for month in [1, 2, 3]:
            result = calculate_distributed_amount(defn, 2025, month, db_session)
            total += result.amount

        assert total == pytest.approx(8295.0, abs=0.01)

    def test_missing_invoice_warns(self, db_session):
        _seed_basic_data(db_session)
        db_session.commit()

        defn = db_session.query(LineItemDefinition).filter_by(position=4).first()
        result = calculate_distributed_amount(defn, 2025, 7, db_session)
        assert result.amount == 0.0
        assert len(result.warnings) == 1


class TestUpworkAmount:
    def test_sums_transactions(self, db_session):
        _seed_jan_2025_data(db_session)
        db_session.commit()

        defn = db_session.query(LineItemDefinition).filter_by(position=5).first()
        result = calculate_upwork_amount(defn, 2025, 1, db_session)

        expected = 1200.50 + 1500.75 + 1100.00  # = 3801.25
        assert result.amount == pytest.approx(expected, abs=0.01)
        assert result.upwork_tx_ids is not None
        assert len(result.upwork_tx_ids) == 3

    def test_no_transactions_warns(self, db_session):
        _seed_basic_data(db_session)
        db_session.commit()

        defn = db_session.query(LineItemDefinition).filter_by(position=5).first()
        result = calculate_upwork_amount(defn, 2025, 7, db_session)
        assert result.amount == 0.0
        assert len(result.warnings) == 1


class TestResolveLineItems:
    def test_resolves_all_positions(self, db_session):
        _seed_jan_2025_data(db_session)
        db_session.commit()

        preview = resolve_line_items("drs", 2025, 1, db_session)
        assert isinstance(preview, InvoicePreview)
        assert len(preview.items) == 6  # 6 line item definitions

        # Check fixed items
        assert preview.items[0].amount == 16450.0
        assert preview.items[1].amount == 8300.0

        # Check direct (Junior FM)
        assert preview.items[2].amount == 1300.0

        # Check distributed (Kaletsch)
        assert preview.items[3].amount > 0

        # Check Upwork
        assert preview.items[4].amount == pytest.approx(3801.25, abs=0.01)

        # Check Aeologic (USD direct)
        assert preview.items[5].amount == 899.89

    def test_vat_calculation(self, db_session):
        _seed_jan_2025_data(db_session)
        db_session.commit()

        preview = resolve_line_items("drs", 2025, 1, db_session)

        # VAT should be round(net * 0.19, 2)
        expected_vat = float(
            (Decimal(str(preview.net_total)) * Decimal("0.19")).quantize(
                Decimal("0.01")
            )
        )
        assert preview.vat_amount == pytest.approx(expected_vat, abs=0.01)
        assert preview.gross_total == pytest.approx(
            preview.net_total + preview.vat_amount, abs=0.01
        )

    def test_totals_are_consistent(self, db_session):
        _seed_jan_2025_data(db_session)
        db_session.commit()

        preview = resolve_line_items("drs", 2025, 1, db_session)

        # Net should equal sum of item amounts
        item_sum = sum(item.amount for item in preview.items)
        assert preview.net_total == pytest.approx(item_sum, abs=0.01)

        # Gross = Net + VAT
        assert preview.gross_total == pytest.approx(
            preview.net_total + preview.vat_amount, abs=0.01
        )
