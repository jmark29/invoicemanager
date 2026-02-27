"""Phase 7 tests: MCP server tools and resources.

Tests each MCP tool and resource function by calling them directly
with a seeded in-memory database, verifying returned text contains
expected content.
"""

from contextlib import contextmanager
from datetime import date
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from backend.models.generated_invoice import GeneratedInvoice
from backend.models.payment_receipt import PaymentReceipt
from backend.seed.loader import seed_all


# ── Fixtures ────────────────────────────────────────────────────


@pytest.fixture
def seeded_db(db_session: Session) -> Session:
    """Seed the test database with all historical data."""
    loaded = seed_all(db_session)
    assert loaded is True
    return db_session


@pytest.fixture(autouse=True)
def _patch_mcp_session(seeded_db, db_engine):
    """Patch get_session so all MCP tools use the test database."""
    from sqlalchemy.orm import sessionmaker

    TestSession = sessionmaker(bind=db_engine, autoflush=False, expire_on_commit=False)

    @contextmanager
    def _test_session():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    with patch("mcp_server.db.get_session", _test_session):
        yield


# ── Query Tool Tests ────────────────────────────────────────────


class TestQueryTools:
    def test_get_working_days_jan_2025(self):
        from mcp_server.tools_query import get_working_days

        result = get_working_days(2025, 1)
        assert "22 Arbeitstage" in result
        assert "Januar 2025" in result

    def test_get_working_days_feb_2025(self):
        from mcp_server.tools_query import get_working_days

        result = get_working_days(2025, 2)
        assert "20 Arbeitstage" in result

    def test_get_month_overview_jan_2025(self):
        from mcp_server.tools_query import get_month_overview

        result = get_month_overview("2025-01")
        assert "Januar 2025" in result
        # Should have all 6 regular positions + optional
        assert "Pos 1" in result
        assert "Pos 2" in result
        assert "Pos 3" in result
        assert "Pos 4" in result
        assert "Pos 5" in result
        assert "Pos 6" in result
        # Fixed amounts should be present
        assert "16.450,00" in result
        assert "8.300,00" in result
        # Should show "nicht generiert" since no invoice generated
        assert "nicht generiert" in result

    def test_get_month_overview_shows_net_total(self):
        from mcp_server.tools_query import get_month_overview

        result = get_month_overview("2025-01")
        assert "Netto" in result
        assert "Brutto" in result
        assert "19%" in result

    def test_get_open_invoices_none(self):
        from mcp_server.tools_query import get_open_invoices

        result = get_open_invoices()
        assert "Keine offenen Rechnungen" in result

    def test_get_category_costs_junior_fm(self):
        from mcp_server.tools_query import get_category_costs

        result = get_category_costs("junior_fm")
        assert "Kategorie:" in result
        assert "direct" in result
        assert "Rechnungen:" in result

    def test_get_category_costs_with_month_filter(self):
        from mcp_server.tools_query import get_category_costs

        result = get_category_costs("junior_fm", from_month="2025-01", to_month="2025-03")
        assert "Rechnungen:" in result

    def test_get_category_costs_upwork(self):
        from mcp_server.tools_query import get_category_costs

        result = get_category_costs("upwork_mobile")
        assert "upwork" in result.lower()
        assert "Upwork-Transaktionen:" in result

    def test_get_category_costs_invalid(self):
        from mcp_server.tools_query import get_category_costs

        result = get_category_costs("nonexistent")
        assert "nicht gefunden" in result

    def test_get_upwork_summary(self):
        from mcp_server.tools_query import get_upwork_summary

        result = get_upwork_summary("2025-01")
        assert "Januar 2025" in result
        assert "Summe:" in result

    def test_get_upwork_summary_empty_month(self):
        from mcp_server.tools_query import get_upwork_summary

        result = get_upwork_summary("2024-01")
        assert "Keine Upwork-Transaktionen" in result

    def test_search_transactions_bank(self):
        from mcp_server.tools_query import search_transactions

        # Seed data should have bank transactions with various descriptions
        result = search_transactions("Kaletsch", transaction_type="bank")
        assert "Banktransaktionen" in result

    def test_search_transactions_both(self):
        from mcp_server.tools_query import search_transactions

        result = search_transactions("test")
        assert "Banktransaktionen" in result
        assert "Upwork-Transaktionen" in result

    def test_get_distribution_q1_2025(self):
        from mcp_server.tools_query import get_distribution

        result = get_distribution(8295.00, ["2025-01", "2025-02", "2025-03"])
        assert "8.295,00" in result
        assert "Januar 2025" in result
        assert "Februar 2025" in result
        assert "März 2025" in result
        assert "Arbeitstage gesamt:" in result
        assert "63" in result  # 22 + 20 + 21

    def test_get_reconciliation(self):
        from mcp_server.tools_query import get_reconciliation

        result = get_reconciliation("2025-01")
        assert "Abstimmung" in result
        assert "Januar 2025" in result

    def test_get_missing_data(self):
        from mcp_server.tools_query import get_missing_data

        result = get_missing_data("2025-01")
        assert "Fehlende Daten" in result
        # Invoice not generated yet
        assert "nicht generiert" in result

    def test_get_invoice_status_no_params(self):
        from mcp_server.tools_query import get_invoice_status

        result = get_invoice_status()
        assert "Fehler" in result or "Bitte" in result

    def test_get_invoice_status_not_found(self):
        from mcp_server.tools_query import get_invoice_status

        result = get_invoice_status(invoice_number="999999-99")
        assert "Keine Rechnung" in result


# ── Action Tool Tests ───────────────────────────────────────────


class TestActionTools:
    def test_generate_invoice_success(self):
        from mcp_server.tools_action import generate_invoice

        with patch("backend.services.invoice_engine.render_and_save_pdf"):
            result = generate_invoice(
                month="2025-01",
                invoice_date="2025-01-28",
            )
        assert "erfolgreich generiert" in result
        assert "202501-02" in result
        assert "Januar 2025" in result

    def test_generate_invoice_duplicate(self):
        from mcp_server.tools_action import generate_invoice

        with patch("backend.services.invoice_engine.render_and_save_pdf"):
            generate_invoice(month="2025-02", invoice_date="2025-02-28")
            result = generate_invoice(month="2025-02", invoice_date="2025-02-28")
        assert "Fehler" in result
        assert "already exists" in result or "bereits" in result.lower()

    def test_update_invoice_status(self):
        from mcp_server.tools_action import generate_invoice, update_invoice_status

        with patch("backend.services.invoice_engine.render_and_save_pdf"):
            generate_invoice(month="2025-03", invoice_date="2025-03-28")

        result = update_invoice_status(
            status="sent",
            invoice_number="202503-02",
        )
        assert "aktualisiert" in result
        assert "draft" in result
        assert "sent" in result

    def test_update_invoice_status_invalid(self):
        from mcp_server.tools_action import update_invoice_status

        result = update_invoice_status(status="invalid_status", invoice_number="202501-02")
        assert "Fehler" in result
        assert "Ungültiger Status" in result

    def test_record_provider_invoice(self):
        from mcp_server.tools_action import record_provider_invoice

        result = record_provider_invoice(
            category_id="junior_fm",
            invoice_number="TEST-INV-001",
            invoice_date="2025-07-15",
            amount=1350.00,
        )
        assert "erfasst" in result
        assert "TEST-INV-001" in result
        assert "1.350,00" in result

    def test_record_provider_invoice_invalid_category(self):
        from mcp_server.tools_action import record_provider_invoice

        result = record_provider_invoice(
            category_id="nonexistent",
            invoice_number="TEST-INV-002",
            invoice_date="2025-07-15",
            amount=100.00,
        )
        assert "nicht gefunden" in result

    def test_record_payment(self):
        from mcp_server.tools_action import record_payment

        result = record_payment(
            client_id="drs",
            amount=42287.60,
            payment_date="2025-02-15",
            reference="ZAHLUNG-JAN-2025",
        )
        assert "erfasst" in result
        assert "42.287,60" in result
        assert "DRS Holding AG" in result

    def test_record_payment_invalid_client(self):
        from mcp_server.tools_action import record_payment

        result = record_payment(
            client_id="nonexistent",
            amount=100.00,
            payment_date="2025-01-15",
        )
        assert "nicht gefunden" in result

    def test_link_bank_payment(self, seeded_db):
        """Test linking requires actual IDs from seed data."""
        from backend.models.bank_transaction import BankTransaction
        from backend.models.provider_invoice import ProviderInvoice
        from mcp_server.tools_action import link_bank_payment

        # Find an unlinked bank transaction
        bank_tx = seeded_db.query(BankTransaction).filter(
            BankTransaction.provider_invoice_id.is_(None)
        ).first()

        inv = seeded_db.query(ProviderInvoice).first()

        if bank_tx and inv:
            result = link_bank_payment(
                bank_transaction_id=bank_tx.id,
                provider_invoice_id=inv.id,
            )
            assert "Verknüpfung" in result
        else:
            # If all are linked in seed data, test with invalid IDs
            result = link_bank_payment(bank_transaction_id=99999, provider_invoice_id=99999)
            assert "nicht gefunden" in result

    def test_link_bank_payment_not_found(self):
        from mcp_server.tools_action import link_bank_payment

        result = link_bank_payment(bank_transaction_id=99999, provider_invoice_id=99999)
        assert "nicht gefunden" in result

    def test_get_invoice_status_after_generate(self):
        """After generating an invoice, get_invoice_status should find it."""
        from mcp_server.tools_action import generate_invoice
        from mcp_server.tools_query import get_invoice_status

        with patch("backend.services.invoice_engine.render_and_save_pdf"):
            generate_invoice(month="2025-04", invoice_date="2025-04-28")

        result = get_invoice_status(invoice_number="202504-02")
        assert "202504-02" in result
        assert "draft" in result
        assert "Netto" in result

    def test_get_open_invoices_after_generate(self):
        """After generating an invoice, it should show in open invoices."""
        from mcp_server.tools_action import generate_invoice
        from mcp_server.tools_query import get_open_invoices

        with patch("backend.services.invoice_engine.render_and_save_pdf"):
            generate_invoice(month="2025-05", invoice_date="2025-05-28")

        result = get_open_invoices()
        assert "202505-02" in result
        assert "draft" in result


# ── Resource Tests ──────────────────────────────────────────────


class TestResources:
    def test_monthly_overview_resource(self):
        from mcp_server.resources import monthly_overview

        result = monthly_overview("2025-01")
        assert "# Monatsübersicht" in result
        assert "Januar 2025" in result
        assert "| Pos |" in result  # Markdown table
        assert "16.450,00" in result  # Fixed PM amount
        assert "Brutto" in result

    def test_client_info_resource(self):
        from mcp_server.resources import client_info

        result = client_info("drs")
        assert "# DRS Holding AG" in result
        assert "Kundennummer: 02" in result
        assert "Hamburg" in result
        assert "Rechnungspositionen" in result

    def test_client_info_not_found(self):
        from mcp_server.resources import client_info

        result = client_info("nonexistent")
        assert "nicht gefunden" in result

    def test_category_info_resource(self):
        from mcp_server.resources import category_info

        result = category_info("junior_fm")
        assert "Junior Facility Management" in result or "junior_fm" in result
        assert "direct" in result
        assert "Lieferantenrechnungen" in result

    def test_category_info_upwork(self):
        from mcp_server.resources import category_info

        result = category_info("upwork_mobile")
        assert "upwork" in result.lower()
        assert "Upwork-Transaktionen" in result

    def test_category_info_not_found(self):
        from mcp_server.resources import category_info

        result = category_info("nonexistent")
        assert "nicht gefunden" in result
