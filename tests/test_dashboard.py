"""Phase 8 tests: dashboard endpoints, reconciliation service, file upload validation."""

from datetime import date

import pytest
from sqlalchemy.orm import Session

from backend.models.bank_transaction import BankTransaction
from backend.models.client import Client
from backend.models.cost_category import CostCategory
from backend.models.generated_invoice import GeneratedInvoice, GeneratedInvoiceItem
from backend.models.payment_receipt import PaymentReceipt
from backend.models.provider_invoice import ProviderInvoice
from backend.services.reconciliation import reconcile_month


# ── Fixtures ─────────────────────────────────────────────────────


@pytest.fixture
def seed_drs(db_session: Session) -> Client:
    c = Client(
        id="drs",
        client_number="02",
        name="DRS Holding AG",
        address_line1="Am Sandtorkai 58",
        zip_city="20457 Hamburg",
        vat_rate=0.19,
    )
    db_session.add(c)
    db_session.commit()
    return c


@pytest.fixture
def seed_category(db_session: Session) -> CostCategory:
    cat = CostCategory(
        id="junior_fm",
        name="Junior FM",
        cost_type="direct",
        currency="EUR",
        billing_cycle="monthly",
        sort_order=1,
    )
    db_session.add(cat)
    db_session.commit()
    return cat


@pytest.fixture
def seed_invoice(db_session: Session, seed_drs: Client) -> GeneratedInvoice:
    """Create a generated invoice for Jan 2025."""
    inv = GeneratedInvoice(
        client_id="drs",
        invoice_number="202501-02",
        invoice_number_display="Rechnung 202501-02",
        period_year=2025,
        period_month=1,
        invoice_date=date(2025, 1, 31),
        net_total=35535.80,
        vat_amount=6751.80,
        gross_total=42287.60,
        status="sent",
    )
    db_session.add(inv)
    db_session.flush()

    items = [
        GeneratedInvoiceItem(invoice_id=inv.id, position=1, label="PM", amount=16450.00, source_type="fixed"),
        GeneratedInvoiceItem(invoice_id=inv.id, position=2, label="Senior FM", amount=8300.00, source_type="fixed"),
    ]
    db_session.add_all(items)
    db_session.commit()
    return inv


@pytest.fixture
def seed_provider_invoice(db_session: Session, seed_category: CostCategory) -> ProviderInvoice:
    """Create a provider invoice for Jan 2025."""
    inv = ProviderInvoice(
        category_id="junior_fm",
        invoice_number="01/2025",
        amount=1800.00,
        currency="EUR",
        invoice_date=date(2025, 1, 15),
        assigned_month="2025-01",
    )
    db_session.add(inv)
    db_session.commit()
    return inv


# ── Reconciliation Service Tests ────────────────────────────────


class TestReconciliation:
    def test_empty_month(self, db_session: Session, seed_category):
        """A month with no data returns empty reconciliation."""
        result = reconcile_month(2025, 12, db_session)
        assert result.matched_count == 0
        assert result.unmatched_count == 0
        assert result.provider_matches == []
        assert result.unmatched_bank_transactions == []
        assert result.invoice_status is None

    def test_matched_provider_invoice(
        self, db_session: Session, seed_provider_invoice: ProviderInvoice
    ):
        """Provider invoice with linked bank transaction shows as matched."""
        bt = BankTransaction(
            booking_date=date(2025, 1, 20),
            value_date=date(2025, 1, 20),
            transaction_type="Überweisung",
            description="Junior FM payment",
            amount_eur=-1800.00,
            category_id="junior_fm",
            provider_invoice_id=seed_provider_invoice.id,
        )
        db_session.add(bt)
        db_session.commit()

        result = reconcile_month(2025, 1, db_session)
        assert result.matched_count == 1
        assert result.unmatched_count == 0
        assert len(result.provider_matches) == 1
        m = result.provider_matches[0]
        assert m.has_bank_payment is True
        assert m.bank_amount == 1800.00
        assert m.invoice_number == "01/2025"

    def test_unmatched_provider_invoice(
        self, db_session: Session, seed_provider_invoice
    ):
        """Provider invoice without bank transaction shows as unmatched."""
        result = reconcile_month(2025, 1, db_session)
        assert result.matched_count == 0
        assert result.unmatched_count == 1
        assert result.provider_matches[0].has_bank_payment is False

    def test_unmatched_bank_transactions(
        self, db_session: Session, seed_category
    ):
        """Bank transactions without provider link appear in unmatched list."""
        bt = BankTransaction(
            booking_date=date(2025, 1, 20),
            value_date=date(2025, 1, 20),
            transaction_type="Überweisung",
            description="Mystery payment",
            amount_eur=-500.00,
            category_id="junior_fm",
        )
        db_session.add(bt)
        db_session.commit()

        result = reconcile_month(2025, 1, db_session)
        assert len(result.unmatched_bank_transactions) == 1
        assert result.unmatched_bank_transactions[0].amount_eur == 500.00

    def test_invoice_payment_status(self, db_session: Session, seed_invoice):
        """Invoice with payment shows correct balance."""
        payment = PaymentReceipt(
            client_id="drs",
            matched_invoice_id=seed_invoice.id,
            amount_eur=20000.00,
            payment_date=date(2025, 2, 15),
            notes="Teilzahlung",
        )
        db_session.add(payment)
        db_session.commit()

        result = reconcile_month(2025, 1, db_session)
        assert result.invoice_status is not None
        assert result.invoice_status.total_paid == 20000.00
        assert result.invoice_status.balance == pytest.approx(42287.60 - 20000.00)

    def test_no_invoice_status(self, db_session: Session, seed_category):
        """Month without generated invoice returns None for invoice_status."""
        result = reconcile_month(2025, 1, db_session)
        assert result.invoice_status is None


# ── Dashboard API Tests ─────────────────────────────────────────


class TestDashboardMonthly:
    def test_month_with_invoice(self, client, db_session, seed_invoice):
        resp = client.get("/api/dashboard/monthly/2025/1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["has_invoice"] is True
        assert data["net_total"] == pytest.approx(35535.80)
        assert data["gross_total"] == pytest.approx(42287.60)
        assert data["invoice"]["invoice_number"] == "202501-02"
        assert len(data["items"]) == 2

    def test_month_without_invoice(self, client, db_session, seed_drs):
        resp = client.get("/api/dashboard/monthly/2025/12")
        assert resp.status_code == 200
        data = resp.json()
        assert data["has_invoice"] is False
        assert data["items"] == []
        assert data["net_total"] == 0.0


class TestDashboardOpenInvoices:
    def test_returns_unpaid(self, client, db_session, seed_invoice):
        """Invoice with status='sent' should appear in open invoices."""
        resp = client.get("/api/dashboard/open-invoices")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        assert data["total_gross"] == pytest.approx(42287.60)

    def test_excludes_paid(self, client, db_session, seed_invoice, seed_drs):
        """Paid invoice should not appear."""
        seed_invoice.status = "paid"
        db_session.commit()

        resp = client.get("/api/dashboard/open-invoices")
        data = resp.json()
        assert data["count"] == 0

    def test_empty(self, client, db_session, seed_drs):
        resp = client.get("/api/dashboard/open-invoices")
        data = resp.json()
        assert data["count"] == 0
        assert data["invoices"] == []


class TestDashboardReconciliation:
    def test_reconciliation_endpoint(
        self, client, db_session, seed_provider_invoice, seed_invoice
    ):
        resp = client.get("/api/dashboard/reconciliation/2025/1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["year"] == 2025
        assert data["month"] == 1
        assert data["unmatched_count"] == 1  # provider invoice without bank tx
        assert data["invoice_status"]["invoice_number"] == "202501-02"

    def test_empty_reconciliation(self, client, db_session, seed_category):
        resp = client.get("/api/dashboard/reconciliation/2025/12")
        assert resp.status_code == 200
        data = resp.json()
        assert data["matched_count"] == 0
        assert data["unmatched_count"] == 0
        assert data["invoice_status"] is None


# ── Upload Validation Integration Tests ─────────────────────────


class TestUploadValidation:
    def test_bank_import_rejects_csv(self, client, db_session, seed_drs):
        resp = client.post(
            "/api/bank-transactions/import",
            files={"file": ("data.csv", b"a,b,c", "text/csv")},
        )
        assert resp.status_code == 400
        assert ".csv" in resp.json()["detail"]

    def test_upwork_import_rejects_csv(self, client, db_session, seed_drs):
        resp = client.post(
            "/api/upwork-transactions/import",
            files={"file": ("data.txt", b"text", "text/plain")},
        )
        assert resp.status_code == 400

    def test_provider_upload_rejects_docx(self, client, db_session, seed_provider_invoice):
        resp = client.post(
            f"/api/provider-invoices/{seed_provider_invoice.id}/upload",
            files={"file": ("doc.docx", b"fake", "application/octet-stream")},
        )
        assert resp.status_code == 400
        assert ".docx" in resp.json()["detail"]
