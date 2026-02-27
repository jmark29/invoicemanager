"""Phase 5 seed data — all constants from tracking.json, config.json, and blueprint.

This module defines the raw data for seeding the database with historical
records for Jan-Jun 2025 validation. The loader module uses these constants
to create ORM objects.
"""

from datetime import date

# ── Client ──────────────────────────────────────────────────────

CLIENT_DRS = {
    "id": "drs",
    "client_number": "02",
    "name": "DRS Holding AG",
    "address_line1": "Am Sandtorkai 58",
    "address_line2": "",
    "zip_city": "20457 Hamburg",
    "vat_rate": 0.19,
}


# ── Cost Categories ─────────────────────────────────────────────

COST_CATEGORIES = [
    {
        "id": "junior_fm",
        "name": "Junior FileMaker Entwickler",
        "provider_name": "Mikhail Iakovlev",
        "provider_location": "Wien, Österreich",
        "currency": "EUR",
        "hourly_rate": 50.0,
        "rate_currency": "EUR",
        "billing_cycle": "monthly",
        "cost_type": "direct",
        "vat_status": "exempt",  # Kleinunternehmerregelung
        "bank_keywords": ["Iakovlev", "Mikhail"],
        "sort_order": 1,
    },
    {
        "id": "cloud_engineer",
        "name": "Serveradministration und AWS-Services",
        "provider_name": "The Kaletsch Company Pty Ltd",
        "provider_location": "Gillitts, South Africa",
        "currency": "EUR",
        "hourly_rate": 36.0,
        "rate_currency": "EUR",
        "billing_cycle": "quarterly",
        "cost_type": "distributed",
        "distribution_method": "working_days",
        "vat_status": "reverse_charge",
        "bank_keywords": ["Kaletsch", "KALETSCH"],
        "sort_order": 2,
    },
    {
        "id": "upwork_mobile",
        "name": "Mobile Softwareentwickler",
        "provider_name": "Upwork (Freelancer)",
        "currency": "EUR",
        "billing_cycle": "weekly",
        "cost_type": "upwork",
        "vat_status": "standard",
        "bank_keywords": ["Upwork", "UPWORK"],
        "sort_order": 3,
    },
    {
        "id": "aeologic",
        "name": "2. Mobile Softwareentwickler, QA- und Business Analyst Services",
        "provider_name": "Aeologic Technologies Pvt. Ltd.",
        "provider_location": "Noida, India",
        "currency": "USD",
        "hourly_rate": 25.0,  # 25 EUR/h initially, 28 from mid-2025
        "rate_currency": "EUR",
        "billing_cycle": "irregular",
        "cost_type": "direct",
        "vat_status": "reverse_charge",
        "bank_keywords": ["Aeologic", "AEOLOGIC", "AEO"],
        "sort_order": 4,
    },
]


# ── Line Item Definitions ───────────────────────────────────────

LINE_ITEM_DEFINITIONS = [
    {
        "client_id": "drs",
        "position": 1,
        "label": "Team- & Projektmanagement und Konzeption",
        "source_type": "fixed",
        "fixed_amount": 16450.00,
        "is_optional": False,
        "sort_order": 1,
    },
    {
        "client_id": "drs",
        "position": 2,
        "label": "Senior FileMaker Entwickler",
        "source_type": "fixed",
        "fixed_amount": 8300.00,
        "is_optional": False,
        "sort_order": 2,
    },
    {
        "client_id": "drs",
        "position": 3,
        "label": "Junior FileMaker Entwickler",
        "source_type": "category",
        "category_id": "junior_fm",
        "is_optional": False,
        "sort_order": 3,
    },
    {
        "client_id": "drs",
        "position": 4,
        "label": "Serveradministration und AWS-Services",
        "source_type": "category",
        "category_id": "cloud_engineer",
        "is_optional": False,
        "sort_order": 4,
    },
    {
        "client_id": "drs",
        "position": 5,
        "label": "Mobile Softwareentwickler",
        "source_type": "category",
        "category_id": "upwork_mobile",
        "is_optional": False,
        "sort_order": 5,
    },
    {
        "client_id": "drs",
        "position": 6,
        "label": "2. Mobile Softwareentwickler, QA- und Business Analyst Services",
        "source_type": "category",
        "category_id": "aeologic",
        "is_optional": False,
        "sort_order": 6,
    },
    {
        "client_id": "drs",
        "position": 7,
        "label": "Reisekosten",
        "source_type": "manual",
        "is_optional": True,
        "sort_order": 7,
    },
]


# ── Junior FM Provider Invoices (12 months, direct EUR) ─────────

JUNIOR_FM_INVOICES = [
    {"invoice_number": "01/2025", "invoice_date": date(2025, 1, 31), "assigned_month": "2025-01", "hours": 26, "amount": 1300.0, "file_path": "categories/junior_fm/ER2501-19.pdf"},
    {"invoice_number": "02/2025", "invoice_date": date(2025, 2, 28), "assigned_month": "2025-02", "hours": 76, "amount": 3800.0, "file_path": "categories/junior_fm/ER2502-17.pdf"},
    {"invoice_number": "03/2025", "invoice_date": date(2025, 3, 4),  "assigned_month": "2025-03", "hours": 40, "amount": 2000.0, "file_path": "categories/junior_fm/ER2503-04.pdf"},
    {"invoice_number": "04/2025", "invoice_date": date(2025, 4, 11), "assigned_month": "2025-04", "hours": 40, "amount": 2000.0, "file_path": "categories/junior_fm/ER2504-11.pdf"},
    {"invoice_number": "05/2025", "invoice_date": date(2025, 5, 16), "assigned_month": "2025-05", "hours": 32, "amount": 1600.0, "file_path": "categories/junior_fm/ER2505-16.pdf"},
    {"invoice_number": "06/2025", "invoice_date": date(2025, 6, 16), "assigned_month": "2025-06", "hours": 36, "amount": 1800.0, "file_path": "categories/junior_fm/ER2506-16.pdf"},
    {"invoice_number": "07/2025", "invoice_date": date(2025, 7, 4),  "assigned_month": "2025-07", "hours": 32, "amount": 1600.0, "file_path": "categories/junior_fm/ER2507-04.pdf"},
    {"invoice_number": "08/2025", "invoice_date": date(2025, 8, 12), "assigned_month": "2025-08", "hours": 14, "amount": 700.0,  "file_path": "categories/junior_fm/ER2508-12.pdf"},
    {"invoice_number": "09/2025", "invoice_date": date(2025, 9, 8),  "assigned_month": "2025-09", "hours": 32, "amount": 1600.0, "file_path": "categories/junior_fm/ER2509-08.pdf"},
    {"invoice_number": "10/2025", "invoice_date": date(2025, 10, 2), "assigned_month": "2025-10", "hours": 32, "amount": 1600.0, "file_path": "categories/junior_fm/ER2510-02.pdf"},
    {"invoice_number": "11/2025", "invoice_date": date(2025, 11, 12),"assigned_month": "2025-11", "hours": 32, "amount": 1600.0, "file_path": "categories/junior_fm/ER2511-12.pdf"},
    {"invoice_number": "12/2025", "invoice_date": date(2025, 12, 21),"assigned_month": "2025-12", "hours": 32, "amount": 1600.0, "file_path": "categories/junior_fm/ER2512-21.pdf"},
]


# ── Kaletsch Provider Invoices (4 quarterly, distributed) ───────

KALETSCH_INVOICES = [
    {
        "invoice_number": "INV307",
        "invoice_date": date(2025, 3, 1),
        "hours": 230,
        "amount": 8280.0,
        "covers_months": ["2025-01", "2025-02", "2025-03"],
        "bank_payment": {"booking_date": date(2025, 1, 6), "amount_eur": -8295.0, "fee": 15.0,
                         "description": "ZAHLUNGSGRUND: INV307 THE KALETSCH COMPANY"},
    },
    {
        "invoice_number": "INV308",
        "invoice_date": date(2025, 3, 31),
        "hours": 234,
        "amount": 8424.0,
        "covers_months": ["2025-04", "2025-05", "2025-06"],
        "bank_payment": {"booking_date": date(2025, 4, 14), "amount_eur": -8439.14, "fee": 15.14,
                         "description": "ZAHLUNGSGRUND: INV308 THE KALETSCH COMPANY"},
    },
    {
        "invoice_number": "INV314",
        "invoice_date": date(2025, 7, 1),
        "hours": 260.3,
        "amount": 9370.8,
        "covers_months": ["2025-07", "2025-08", "2025-09"],
        "notes": "Includes 22.7h Q2 adjustment (€817.20)",
        "bank_payment": {"booking_date": date(2025, 7, 15), "amount_eur": -9387.36, "fee": 16.56,
                         "description": "ZAHLUNGSGRUND: INV314 THE KALETSCH COMPANY"},
    },
    {
        "invoice_number": "INV320",
        "invoice_date": date(2025, 9, 30),
        "hours": 237.6,
        "amount": 8553.6,
        "covers_months": ["2025-10", "2025-11", "2025-12"],
        "bank_payment": {"booking_date": date(2025, 10, 20), "amount_eur": -8568.93, "fee": 15.33,
                         "description": "ZAHLUNGSGRUND: INV320 THE KALETSCH COMPANY"},
    },
]


# ── Aeologic Provider Invoices (13 original + 2 synthetic combined) ──

# All 13 original invoices from tracking.json
AEOLOGIC_INVOICES_ORIGINAL = [
    {"invoice_number": "AEO000716", "invoice_date": date(2024, 12, 31), "usd": 900.0,  "hours": None, "rate": 25, "bank_eur": 899.89,  "bank_date": date(2025, 1, 6)},
    {"invoice_number": "AEO000729", "invoice_date": date(2025, 1, 30), "usd": 1650.0, "hours": 66,   "rate": 25, "bank_eur": 1477.40, "bank_date": date(2025, 5, 26)},
    {"invoice_number": "AEO000741", "invoice_date": date(2025, 2, 28), "usd": 1100.0, "hours": 44,   "rate": 25, "bank_eur": 1036.28, "bank_date": date(2025, 3, 31)},
    {"invoice_number": "AEO000749", "invoice_date": date(2025, 3, 25), "usd": 5500.0, "hours": 220,  "rate": 25, "bank_eur": 5079.51, "bank_date": date(2025, 4, 7)},
    {"invoice_number": "AEO000768", "invoice_date": date(2025, 5, 1),  "usd": 9075.0, "hours": 363,  "rate": 25, "bank_eur": 8092.64, "bank_date": date(2025, 5, 23)},
    {"invoice_number": "AEO000777", "invoice_date": date(2025, 5, 30), "usd": 7140.0, "hours": 255,  "rate": 28, "bank_eur": 6122.20, "bank_date": date(2025, 7, 7)},
    {"invoice_number": "AEO000789", "invoice_date": date(2025, 7, 1),  "usd": 2898.0, "hours": 103.5,"rate": 28, "bank_eur": 2512.79, "bank_date": date(2025, 8, 14)},
    {"invoice_number": "AEO000802", "invoice_date": date(2025, 8, 15), "usd": None,   "hours": None,  "rate": 28, "bank_eur": 1273.66, "bank_date": date(2025, 8, 14), "notes": "No invoice PDF found"},
    {"invoice_number": "AEO000811", "invoice_date": date(2025, 8, 29), "usd": 1456.0, "hours": 52,   "rate": 28, "bank_eur": 1276.43, "bank_date": date(2025, 9, 26)},
    {"invoice_number": "AEO000819", "invoice_date": date(2025, 9, 30), "usd": 784.0,  "hours": 28,   "rate": 28, "bank_eur": None, "notes": "No bank payment found yet"},
    {"invoice_number": "AEO000828", "invoice_date": date(2025, 10, 31),"usd": 1246.0, "hours": 44.5, "rate": 28, "bank_eur": None, "notes": "No bank payment found yet"},
    {"invoice_number": "AEO000844", "invoice_date": date(2025, 12, 1), "usd": 812.0,  "hours": 29,   "rate": 28, "bank_eur": None, "notes": "No bank payment found yet"},
    {"invoice_number": "AEO000852", "invoice_date": date(2025, 12, 30),"usd": 1302.0, "hours": 46.5, "rate": 28, "bank_eur": None, "notes": "No bank payment found yet"},
    # AEO000861 is dated 2026, outside our primary seed range
]

# DRS month mapping: which invoice(s) and EUR amounts map to each DRS billing month.
# For months with unclear sources, we create combined/synthetic provider invoices.
AEOLOGIC_DRS_MONTH_MAPPING = [
    {
        "assigned_month": "2025-01",
        "invoice_number": "AEO-JAN2025-COMBINED",
        "invoice_date": date(2025, 1, 31),
        "amount_usd": None,
        "bank_eur": 1551.41,
        "bank_date": date(2025, 1, 31),
        "notes": "Nicht eindeutig zuordenbar: AEO000716 (€899.89) + Vorgänger-RE?",
    },
    {
        "assigned_month": "2025-02",
        "invoice_number": "AEO000741",  # uses original invoice
        "invoice_date": date(2025, 2, 28),
        "amount_usd": 1100.0,
        "bank_eur": 1036.28,
        "bank_date": date(2025, 3, 31),
    },
    {
        "assigned_month": "2025-03",
        "invoice_number": "AEO000749",
        "invoice_date": date(2025, 3, 25),
        "amount_usd": 5500.0,
        "bank_eur": 5079.51,
        "bank_date": date(2025, 4, 7),
    },
    {
        "assigned_month": "2025-04",
        "invoice_number": "AEO-APR2025-COMBINED",
        "invoice_date": date(2025, 4, 30),
        "amount_usd": None,
        "bank_eur": 8238.89,
        "bank_date": date(2025, 5, 26),
        "notes": "Kombination unklar: AEO000768 + AEO000729?",
    },
    {
        "assigned_month": "2025-05",
        "invoice_number": "AEO000777",
        "invoice_date": date(2025, 5, 30),
        "amount_usd": 7140.0,
        "bank_eur": 6122.20,
        "bank_date": date(2025, 7, 7),
    },
    {
        "assigned_month": "2025-06",
        "invoice_number": "AEO000789",
        "invoice_date": date(2025, 7, 1),
        "amount_usd": 2898.0,
        "bank_eur": 2512.79,
        "bank_date": date(2025, 8, 14),
    },
]


# ── Upwork Transactions (synthetic per-month totals for validation) ──

UPWORK_MONTHLY_TOTALS = [
    {"month": "2025-01", "amount_eur": 5083.19, "tx_date": date(2025, 1, 31)},
    {"month": "2025-02", "amount_eur": 4200.84, "tx_date": date(2025, 2, 28)},
    {"month": "2025-03", "amount_eur": 3843.43, "tx_date": date(2025, 3, 31)},
    {"month": "2025-04", "amount_eur": 3884.03, "tx_date": date(2025, 4, 30)},
    {"month": "2025-05", "amount_eur": 4145.25, "tx_date": date(2025, 5, 31)},
    {"month": "2025-06", "amount_eur": 4673.70, "tx_date": date(2025, 6, 30)},
]


# ── Working Days Config ─────────────────────────────────────────

WORKING_DAYS_CONFIG = {"country": "DE", "state": "HE", "description": "Hessen, Germany"}


# ── Validation Targets (from tracking.json generated_invoices) ──

EXPECTED_INVOICES = {
    "2025-01": {
        "invoice_number": "202501-02",
        "invoice_date": date(2025, 2, 28),
        "line_items": {1: 16450.0, 2: 8300.0, 3: 1300.0, 4: 2851.20, 5: 5083.19, 6: 1551.41},
        "net_total": 35535.80,
        "vat_amount": 6751.80,
        "gross_total": 42287.60,
    },
    "2025-02": {
        "invoice_number": "202502-02",
        "invoice_date": date(2025, 3, 22),
        "line_items": {1: 16450.0, 2: 8300.0, 3: 3800.0, 4: 2592.0, 5: 4200.84, 6: 1036.28, 7: 286.97},
        "net_total": 36666.09,
        "vat_amount": 6966.56,
        "gross_total": 43632.65,
    },
    "2025-03": {
        "invoice_number": "202503-02",
        "invoice_date": date(2025, 4, 10),
        "line_items": {1: 16450.0, 2: 8300.0, 3: 2000.0, 4: 2851.80, 5: 3843.43, 6: 5079.51},
        "net_total": 38524.74,
        "vat_amount": 7319.70,
        "gross_total": 45844.44,
    },
    "2025-04": {
        "invoice_number": "202504-02",
        "invoice_date": date(2025, 5, 12),
        "line_items": {1: 16450.0, 2: 8300.0, 3: 2000.0, 4: 2851.20, 5: 3884.03, 6: 8238.89},
        "net_total": 41724.12,
        "vat_amount": 7927.58,
        "gross_total": 49651.70,
    },
    "2025-05": {
        "invoice_number": "202505-02",
        "invoice_date": date(2025, 7, 7),
        "line_items": {1: 16450.0, 2: 8300.0, 3: 1600.0, 4: 2851.20, 5: 4145.25, 6: 6122.20},
        "net_total": 39468.65,
        "vat_amount": 7499.04,
        "gross_total": 46967.69,
    },
    "2025-06": {
        "invoice_number": "202506-02",
        "invoice_date": date(2025, 9, 5),
        "line_items": {1: 16450.0, 2: 8300.0, 3: 1800.0, 4: 2851.20, 5: 4673.70, 6: 2512.79},
        "net_total": 36587.69,
        "vat_amount": 6951.66,
        "gross_total": 43539.35,
    },
}

# Overrides needed to match historical amounts (Pos 4 algorithmic distribution
# differs from original manual process; Pos 7 Reisekosten only for Feb 2025).
HISTORICAL_OVERRIDES: dict[str, dict[int, float]] = {
    "2025-01": {4: 2851.20},
    "2025-02": {4: 2592.00, 7: 286.97},
    "2025-03": {4: 2851.80},
    "2025-04": {4: 2851.20},
    "2025-05": {4: 2851.20},
    "2025-06": {4: 2851.20},
}

# Auto-computed net totals (algorithmic Kaletsch distribution, no overrides).
# These values differ from historical because the original manual process
# used different Pos 4 amounts than the working-days algorithm produces.
AUTO_COMPUTED_NET_TOTALS = {
    "2025-01": 35581.27,  # Pos 4 auto: 2896.67 vs historical 2851.20
    "2025-02": 36420.45,  # Pos 4 auto: 2633.33 vs historical 2592.00 (no Reisekosten)
    "2025-03": 38437.94,  # Pos 4 auto: 2765.00 vs historical 2851.80
    "2025-04": 41733.65,  # Pos 4 auto: 2860.73 vs historical 2851.20
    "2025-05": 39478.18,  # Pos 4 auto: 2860.73 vs historical 2851.20
    "2025-06": 36454.17,  # Pos 4 auto: 2717.68 vs historical 2851.20
}
