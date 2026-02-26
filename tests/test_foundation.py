"""Phase 1 verification: database creates correctly, health endpoint works, models are consistent."""

from sqlalchemy import inspect

from backend.models import (
    BankTransaction,
    Client,
    CostCategory,
    GeneratedInvoice,
    GeneratedInvoiceItem,
    LineItemDefinition,
    PaymentReceipt,
    ProviderInvoice,
    UpworkTransaction,
    WorkingDaysConfig,
)


def test_health_endpoint(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_all_tables_created(db_engine):
    inspector = inspect(db_engine)
    table_names = set(inspector.get_table_names())
    expected = {
        "clients",
        "cost_categories",
        "line_item_definitions",
        "provider_invoices",
        "bank_transactions",
        "upwork_transactions",
        "generated_invoices",
        "generated_invoice_items",
        "payment_receipts",
        "working_days_config",
    }
    assert expected.issubset(table_names), f"Missing tables: {expected - table_names}"


def test_insert_and_read_client(db_session):
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

    result = db_session.get(Client, "drs")
    assert result is not None
    assert result.name == "DRS Holding AG"
    assert result.vat_rate == 0.19


def test_cost_category_bank_keywords(db_session):
    cat = CostCategory(
        id="cloud_engineer",
        name="Cloud Engineer",
        billing_cycle="quarterly",
        cost_type="distributed",
    )
    cat.bank_keywords = ["KALETSCH", "RORY KALETSCH", "STOCKVILLE"]
    db_session.add(cat)
    db_session.commit()

    result = db_session.get(CostCategory, "cloud_engineer")
    assert result.bank_keywords == ["KALETSCH", "RORY KALETSCH", "STOCKVILLE"]


def test_provider_invoice_covers_months(db_session):
    # Need a category first (FK)
    cat = CostCategory(
        id="cloud_engineer",
        name="Cloud Engineer",
        billing_cycle="quarterly",
        cost_type="distributed",
    )
    db_session.add(cat)
    db_session.flush()

    from datetime import date

    inv = ProviderInvoice(
        category_id="cloud_engineer",
        invoice_number="INV307",
        invoice_date=date(2025, 3, 1),
        amount=8280.0,
        currency="EUR",
    )
    inv.covers_months = ["2025-01", "2025-02", "2025-03"]
    db_session.add(inv)
    db_session.commit()

    result = db_session.get(ProviderInvoice, inv.id)
    assert result.covers_months == ["2025-01", "2025-02", "2025-03"]
    assert result.assigned_month is None  # Not set for distributed


def test_foreign_key_relationships(db_session):
    """Verify that key FK relationships work end-to-end."""
    from datetime import date

    # Client -> LineItemDefinition -> CostCategory
    c = Client(
        id="drs", client_number="02", name="DRS Holding AG",
        address_line1="Am Sandtorkai 58", zip_city="20457 Hamburg",
    )
    cat = CostCategory(
        id="junior_fm", name="Junior FM", billing_cycle="monthly", cost_type="direct",
    )
    db_session.add_all([c, cat])
    db_session.flush()

    lid = LineItemDefinition(
        client_id="drs", position=3, label="Junior FileMaker Entwickler",
        source_type="category", category_id="junior_fm", sort_order=3,
    )
    db_session.add(lid)
    db_session.commit()

    result = db_session.get(LineItemDefinition, lid.id)
    assert result.client.name == "DRS Holding AG"
    assert result.category.name == "Junior FM"
