# Invoice Manager - Project Conventions

## Overview
Local web app for monthly invoicing. See `docs/BLUEPRINT-Invoice-Manager.md` for full requirements and `docs/implementation-plan.md` for the phased build plan.

## Stack
- **Backend:** Python 3.11+ / FastAPI / SQLAlchemy 2.0 / SQLite
- **Frontend:** React 18 / Tailwind CSS / Vite
- **Invoice PDF:** WeasyPrint (HTML-to-PDF)
- **MCP:** Python `mcp` SDK (FastMCP)

## Project Structure
- `backend/` — FastAPI app (models, schemas, services, routers, seed)
- `frontend/` — React app (Vite)
- `mcp_server/` — MCP server (separate process, shares DB)
- `data/` — Runtime data (SQLite DB, templates, generated invoices, uploads)
- `docs/` — Blueprint, implementation plan, reference docs
- `tests/` — pytest test suite

## Development Commands
```bash
# Backend
uv run uvicorn backend.main:app --reload --port 8000

# Frontend
cd frontend && npm run dev

# Tests
uv run pytest

# Seed data
uv run python -m backend.seed.loader

# MCP server
uv run python -m mcp_server.server
```

## Business Domain — 4 Cost Types

Every variable line item on the invoice is resolved through one of these cost types:

| Cost Type | Example | Logic |
|-----------|---------|-------|
| `fixed` | Pos 1, 2 (PM, Senior FM) | Constant amount from `line_item_definitions.fixed_amount` |
| `direct` | Pos 3 (Junior FM), Pos 6 (Aeologic) | 1:1 pass-through of provider invoice. EUR: use invoice amount. USD: use EUR bank debit amount (includes FX + fees) |
| `distributed` | Pos 4 (Kaletsch/Cloud Engineer) | Quarterly invoice distributed across 3 months by Hessen working days. Base = bank payment (invoice + bank fee). Last month gets remainder. |
| `upwork` | Pos 5 (Mobile Dev) | Sum of Upwork XLSX transactions assigned to the month. Assignment rule: period END date determines month. |

## German Terminology Glossary

| German | English | Context |
|--------|---------|---------|
| Rechnung | Invoice | Invoice number displayed as "Rechnung 202501-02" |
| Leistungszeitraum | Service period | "01.01.2025 bis 31.01.2025" |
| Buchungstext | Transaction description | Bank statement field used for keyword matching |
| Buchungstag / Wertstellung | Booking date / Value date | Bank statement date columns |
| Umsatzart | Transaction type | e.g., "Überweisung" (transfer) |
| Netto-Rechnungsbetrag | Net invoice amount | Sum of all line items |
| Umsatzsteuer | VAT (value-added tax) | 19% for DRS |
| Brutto-Rechnungsbetrag | Gross invoice amount | Net + VAT |
| Arbeitstage | Working days | Mon-Fri minus Hessen public holidays |
| Kleinunternehmerregelung | Small business VAT exemption | Junior FM provider is VAT-exempt |
| Reisekosten | Travel expenses | Optional manual line item |

## Data Model — Key Relationships

```
clients --(1:N)--> line_item_definitions --(N:1)--> cost_categories
clients --(1:N)--> generated_invoices --(1:N)--> generated_invoice_items
cost_categories --(1:N)--> provider_invoices --(1:1?)--> bank_transactions
cost_categories --(1:N)--> upwork_transactions
generated_invoices --(1:N)--> payment_receipts
```

- `provider_invoices.assigned_month` determines which billing month an invoice belongs to (defaults to invoice_date month, overridable)
- `bank_transactions.category_id` is auto-matched via `cost_categories.bank_keywords`
- `generated_invoice_items` links back to source data (provider_invoice_id, upwork_tx_ids_json) for traceability

## Validation Baseline (Jan-Jun 2025)

These 6 historical invoices are the acceptance test. Source: `docs/reference-docs/invoice_data/tracking.json`

| Month | Net | VAT (19%) | Gross |
|-------|-----|-----------|-------|
| 2025-01 | 35,535.80 | 6,751.80 | 42,287.60 |
| 2025-02 | 36,666.09* | 6,966.56 | 43,632.65 |
| 2025-03 | 38,524.74 | 7,319.70 | 45,844.44 |
| 2025-04 | 41,724.12 | 7,927.58 | 49,651.70 |
| 2025-05 | 39,468.65 | 7,499.04 | 46,967.69 |
| 2025-06 | 36,587.69 | 6,951.66 | 43,539.35 |

*Feb 2025 includes Reisekosten 286.97

## Conventions
- SQLAlchemy 2.0 style: `Mapped[]` + `mapped_column()`
- All monetary calculations: `Decimal` with `ROUND_HALF_UP` to 2 decimal places
- German number formatting: `1.234,56 EUR` (period=thousands, comma=decimal)
- Date formatting: `DD.MM.YYYY` (German) on invoices, ISO `YYYY-MM-DD` in API/DB
- API prefix: `/api/`
- Soft-delete for clients and cost categories (active boolean flag)
- File paths in DB are relative to DATA_DIR
- Invoice numbering: `YYYYMM-client_number` (e.g., `202501-02`). Filename prefix `AR` (e.g., `AR202501-02.pdf`). The `AR` prefix appears only in the filename, NOT in the invoice text.

## Architecture Decisions
- **HTML-to-PDF over DOCX editing** — More maintainable, no XML run-splitting issues, HTML preview doubles as in-browser preview before generating
- **`assigned_month` on provider_invoices** — Added to blueprint; needed for irregular invoices (Aeologic) where invoice_date month doesn't always match the billing month
- **MCP server as separate process** — Shares SQLite DB file with FastAPI backend but runs independently; both use the same SQLAlchemy models and services

## Known Gotchas
- WeasyPrint requires system libs on macOS: `brew install pango cairo libffi`
- Upwork XLSX sheet name is `"data"` (not default "Sheet1")
- Bank XLSX Buchungstext contains invoice refs as `"ZAHLUNGSGRUND: INV320"` or `"INVOICE  AEO000811"` (note double space)
- Aeologic month mapping for Jan 2025 (1,551.41) and Apr 2025 (8,238.89) is unclear — tracked in `tracking.json` as "Nicht eindeutig zuordenbar"
- Upwork "Amount in local currency" is EUR despite the column name suggesting otherwise
- Use `uv` for Python package management (not pip directly, due to PEP 668 on macOS)

## Reference Data
- `docs/reference-docs/invoice_data/generate_invoice.py` — Working business logic to reference (working days, distribution, Upwork parsing, EUR formatting)
- `docs/reference-docs/invoice_data/tracking.json` — Historical validation data for all 6 months + Aeologic month mapping
- `docs/reference-docs/invoice_data/config.json` — Client/invoice config
- `docs/reference-docs/AR202506-02.docx` — Reference invoice template (layout to match)
- `docs/reference-docs/upwork-transactions_20260225.xlsx` — Sample Upwork export (214 transactions)
- `docs/reference-docs/Kontoumsätze Aeologic + Kaletsch.xlsx` — Sample bank statement
