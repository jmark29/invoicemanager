"""Idempotent seed loader — populates the database with historical data.

Usage:
    uv run python -m backend.seed.loader

Loads all seed data from seed_data.py into the database. Checks for
existing client record to prevent duplicate seeding.
"""

from sqlalchemy.orm import Session

from backend.models.bank_transaction import BankTransaction
from backend.models.client import Client
from backend.models.cost_category import CostCategory
from backend.models.line_item_definition import LineItemDefinition
from backend.models.provider_invoice import ProviderInvoice
from backend.models.upwork_transaction import UpworkTransaction
from backend.models.working_days_config import WorkingDaysConfig
from backend.seed.seed_data import (
    AEOLOGIC_DRS_MONTH_MAPPING,
    AEOLOGIC_INVOICES_ORIGINAL,
    CLIENT_DRS,
    COST_CATEGORIES,
    JUNIOR_FM_INVOICES,
    KALETSCH_INVOICES,
    LINE_ITEM_DEFINITIONS,
    UPWORK_MONTHLY_TOTALS,
    WORKING_DAYS_CONFIG,
)


def seed_client(db: Session) -> Client:
    """Create the DRS client."""
    client = Client(**CLIENT_DRS)
    db.add(client)
    db.flush()
    return client


def seed_cost_categories(db: Session) -> dict[str, CostCategory]:
    """Create all cost categories."""
    categories = {}
    for cat_data in COST_CATEGORIES:
        data = dict(cat_data)
        keywords = data.pop("bank_keywords", [])
        cat = CostCategory(**data)
        cat.bank_keywords = keywords
        db.add(cat)
        categories[cat.id] = cat
    db.flush()
    return categories


def seed_line_item_definitions(db: Session) -> list[LineItemDefinition]:
    """Create line item definitions for DRS client."""
    definitions = []
    for defn_data in LINE_ITEM_DEFINITIONS:
        defn = LineItemDefinition(**defn_data)
        db.add(defn)
        definitions.append(defn)
    db.flush()
    return definitions


def seed_working_days_config(db: Session) -> WorkingDaysConfig:
    """Create working days configuration."""
    config = WorkingDaysConfig(**WORKING_DAYS_CONFIG)
    db.add(config)
    db.flush()
    return config


def seed_junior_fm_invoices(db: Session) -> list[ProviderInvoice]:
    """Seed Junior FM provider invoices (12 months)."""
    invoices = []
    for inv_data in JUNIOR_FM_INVOICES:
        inv = ProviderInvoice(
            category_id="junior_fm",
            invoice_number=inv_data["invoice_number"],
            invoice_date=inv_data["invoice_date"],
            assigned_month=inv_data["assigned_month"],
            hours=inv_data["hours"],
            hourly_rate=50.0,
            rate_currency="EUR",
            amount=inv_data["amount"],
            currency="EUR",
            file_path=inv_data.get("file_path"),
        )
        db.add(inv)
        invoices.append(inv)
    db.flush()
    return invoices


def seed_kaletsch_invoices(db: Session) -> list[ProviderInvoice]:
    """Seed Kaletsch quarterly invoices with linked bank transactions."""
    invoices = []
    for inv_data in KALETSCH_INVOICES:
        inv = ProviderInvoice(
            category_id="cloud_engineer",
            invoice_number=inv_data["invoice_number"],
            invoice_date=inv_data["invoice_date"],
            hours=inv_data["hours"],
            hourly_rate=36.0,
            rate_currency="EUR",
            amount=inv_data["amount"],
            currency="EUR",
            notes=inv_data.get("notes"),
        )
        inv.covers_months = inv_data["covers_months"]
        db.add(inv)
        db.flush()  # get the id for FK reference

        bp = inv_data["bank_payment"]
        bt = BankTransaction(
            booking_date=bp["booking_date"],
            value_date=bp["booking_date"],
            transaction_type="Überweisung",
            description=bp["description"],
            amount_eur=bp["amount_eur"],
            category_id="cloud_engineer",
            provider_invoice_id=inv.id,
            bank_fee=bp.get("fee"),
        )
        db.add(bt)
        invoices.append(inv)

    db.flush()
    return invoices


def seed_aeologic_invoices(db: Session) -> list[ProviderInvoice]:
    """Seed Aeologic invoices: originals (reference) + DRS month-mapped ones (for calculation).

    Original invoices are seeded without assigned_month (reference data).
    DRS month-mapped invoices have assigned_month set and linked bank transactions
    so the cost calculation engine can resolve them.
    """
    invoices = []

    # Track which invoice numbers are used in DRS mapping (to avoid duplicates)
    drs_mapped_numbers = {m["invoice_number"] for m in AEOLOGIC_DRS_MONTH_MAPPING}

    # Seed original invoices that are NOT used in DRS mapping
    for inv_data in AEOLOGIC_INVOICES_ORIGINAL:
        if inv_data["invoice_number"] in drs_mapped_numbers:
            continue  # will be seeded via DRS mapping below

        inv = ProviderInvoice(
            category_id="aeologic",
            invoice_number=inv_data["invoice_number"],
            invoice_date=inv_data["invoice_date"],
            amount=inv_data["usd"] or 0.0,
            currency="USD",
            hours=inv_data.get("hours"),
            hourly_rate=float(inv_data["rate"]),
            rate_currency="EUR",
            notes=inv_data.get("notes"),
        )
        db.add(inv)
        db.flush()

        # Link bank transaction if payment exists
        if inv_data.get("bank_eur") is not None:
            bt = BankTransaction(
                booking_date=inv_data["bank_date"],
                value_date=inv_data["bank_date"],
                transaction_type="Überweisung",
                description=f"INVOICE  {inv_data['invoice_number']} AEOLOGIC TECHNOLOGIES",
                amount_eur=-abs(inv_data["bank_eur"]),  # negative = outgoing
                category_id="aeologic",
                provider_invoice_id=inv.id,
            )
            db.add(bt)

        invoices.append(inv)

    # Seed DRS month-mapped invoices (with assigned_month + bank transaction)
    for mapping in AEOLOGIC_DRS_MONTH_MAPPING:
        # Find matching original data for rate info
        orig = next(
            (o for o in AEOLOGIC_INVOICES_ORIGINAL if o["invoice_number"] == mapping["invoice_number"]),
            None,
        )
        rate = orig["rate"] if orig else 28
        hours = orig.get("hours") if orig else None

        inv = ProviderInvoice(
            category_id="aeologic",
            invoice_number=mapping["invoice_number"],
            invoice_date=mapping["invoice_date"],
            assigned_month=mapping["assigned_month"],
            amount=mapping.get("amount_usd") or 0.0,
            currency="USD",
            hours=hours,
            hourly_rate=float(rate),
            rate_currency="EUR",
            notes=mapping.get("notes"),
        )
        db.add(inv)
        db.flush()

        # Every DRS-mapped invoice needs a linked bank transaction for USD -> EUR resolution
        bt = BankTransaction(
            booking_date=mapping["bank_date"],
            value_date=mapping["bank_date"],
            transaction_type="Überweisung",
            description=f"INVOICE  {mapping['invoice_number']} AEOLOGIC TECHNOLOGIES",
            amount_eur=-abs(mapping["bank_eur"]),  # negative = outgoing
            category_id="aeologic",
            provider_invoice_id=inv.id,
        )
        db.add(bt)
        invoices.append(inv)

    db.flush()
    return invoices


def seed_upwork_transactions(db: Session) -> list[UpworkTransaction]:
    """Seed synthetic Upwork transactions (one per month with correct totals).

    Real Upwork data has many transactions per month (from XLSX import).
    For seed/validation purposes, we create one aggregate transaction per month
    with the exact total that matches the historical invoice amounts.
    """
    transactions = []
    for tx_data in UPWORK_MONTHLY_TOTALS:
        tx = UpworkTransaction(
            tx_id=f"SEED-UPW-{tx_data['month']}",
            tx_date=tx_data["tx_date"],
            tx_type="Fixed Price",
            description=f"Seed: Monthly total for {tx_data['month']}",
            amount_eur=tx_data["amount_eur"],
            freelancer_name="Mobile Developer",
            category_id="upwork_mobile",
            assigned_month=tx_data["month"],
        )
        db.add(tx)
        transactions.append(tx)
    db.flush()
    return transactions


def seed_all(db: Session) -> bool:
    """Load all seed data into the database.

    Returns True if data was loaded, False if it already existed.
    Idempotent: checks for existing client before proceeding.
    """
    existing = db.get(Client, "drs")
    if existing:
        return False

    seed_client(db)
    seed_cost_categories(db)
    seed_line_item_definitions(db)
    seed_working_days_config(db)
    seed_junior_fm_invoices(db)
    seed_kaletsch_invoices(db)
    seed_aeologic_invoices(db)
    seed_upwork_transactions(db)

    db.commit()
    return True


if __name__ == "__main__":
    from backend.database import SessionLocal
    from backend.models import Base
    from backend.database import engine

    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        loaded = seed_all(db)
        if loaded:
            print("Seed data loaded successfully.")

            # Print summary
            print(f"  Client: {db.query(Client).count()}")
            print(f"  Cost categories: {db.query(CostCategory).count()}")
            print(f"  Line item definitions: {db.query(LineItemDefinition).count()}")
            print(f"  Provider invoices: {db.query(ProviderInvoice).count()}")
            print(f"  Bank transactions: {db.query(BankTransaction).count()}")
            print(f"  Upwork transactions: {db.query(UpworkTransaction).count()}")
        else:
            print("Seed data already loaded (client 'drs' exists). Skipping.")
    finally:
        db.close()
