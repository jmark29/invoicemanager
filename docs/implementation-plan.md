# Invoice Manager - Implementation Plan

## Revision History

| Rev | Date | Description |
|-----|------|-------------|
| 1.0 | 2026-02-26 | Initial plan created from blueprint review + codebase exploration |
| 1.1 | 2026-02-26 | Phase 0 + Phase 1 completed; Phase 2 completed |
| 1.2 | 2026-02-26 | Phase 3 completed |

---

## Context

29ventures GmbH manually assembles monthly invoices for DRS Holding AG. Each invoice has 6 line items (2 fixed, 4 variable) sourced from different providers with different billing cycles, currencies, and formats. This application replaces that manual process with a local web app backed by a relational database, with an MCP server for AI assistant integration.

**Existing assets** (in `docs/reference-docs/`):
- `generate_invoice.py` — Working Python script with DOCX template editing, working days calculation, Upwork parsing, and cost distribution logic. **Reuse as reference for all business logic.**
- `tracking.json` — Complete historical data for Jan-Jun 2025 invoices, provider invoice details, and Aeologic month mappings
- `config.json` — Client config, line item definitions, invoice numbering rules
- 6 reference DOCX invoices (`AR202501-02.docx` through `AR202506-02.docx`)
- Provider invoice PDFs: Junior FM (12), Kaletsch (4), Aeologic (15)
- `upwork-transactions_20260225.xlsx` — 214 transactions, sheet "data", 9 columns
- `Kontoumsaetze Aeologic + Kaletsch.xlsx` — Bank transactions, 7 columns (Buchungstag, Wertstellung, Umsatzart, Buchungstext, Betrag, RK, Buchungsjahr)

**Blueprint update**: Add `assigned_month` TEXT field to `provider_invoices` table (defaults to invoice_date month, overridable for irregular invoices like Aeologic).

---

## Technology Stack

| Layer | Choice |
|-------|--------|
| Backend | Python 3.11+ / FastAPI |
| Database | SQLite via SQLAlchemy 2.0 |
| Frontend | React 18 + Tailwind CSS (Vite) |
| Invoice output | HTML-to-PDF via WeasyPrint |
| MCP Server | Python `mcp` SDK (FastMCP) |

**Key dependencies:** `fastapi`, `uvicorn`, `sqlalchemy>=2.0`, `pydantic>=2.0`, `pydantic-settings`, `python-multipart`, `openpyxl`, `weasyprint`, `jinja2`, `mcp>=1.25`

---

## Project Structure

```
invoicemanager/
├── pyproject.toml
├── .gitignore
├── .env.example
├── CLAUDE.md
├── backend/
│   ├── main.py                         # FastAPI app, CORS, lifespan
│   ├── config.py                       # Settings (DATA_DIR, DB path)
│   ├── database.py                     # Engine, SessionLocal, get_db
│   ├── models/                         # SQLAlchemy ORM (10 tables)
│   │   ├── base.py                     # DeclarativeBase
│   │   ├── client.py
│   │   ├── cost_category.py
│   │   ├── line_item_definition.py
│   │   ├── provider_invoice.py         # + assigned_month field
│   │   ├── bank_transaction.py
│   │   ├── upwork_transaction.py
│   │   ├── generated_invoice.py        # + GeneratedInvoiceItem
│   │   ├── payment_receipt.py
│   │   └── working_days_config.py
│   ├── schemas/                        # Pydantic request/response models
│   ├── services/                       # Business logic
│   │   ├── working_days.py             # Easter + Hessen holidays
│   │   ├── cost_calculation.py         # Per-cost-type amount resolution
│   │   ├── invoice_engine.py           # Preview + generate orchestrator
│   │   ├── invoice_renderer.py         # Jinja2 HTML + WeasyPrint PDF
│   │   ├── upwork_import.py            # XLSX parser
│   │   ├── bank_import.py              # XLSX parser + keyword matching
│   │   └── formatting.py              # German EUR format, dates
│   ├── routers/                        # API endpoints
│   │   ├── clients.py, cost_categories.py, line_item_definitions.py
│   │   ├── provider_invoices.py, bank_transactions.py, upwork_transactions.py
│   │   ├── invoices.py, payments.py, dashboard.py, working_days.py
│   └── seed/
│       ├── seed_data.py                # All constants from tracking.json + blueprint
│       └── loader.py                   # Idempotent seed loading
├── mcp_server/
│   ├── server.py                       # FastMCP entry point
│   ├── tools_query.py                  # 10 read-only tools
│   ├── tools_action.py                 # 7 action tools
│   └── resources.py                    # 3 resources
├── frontend/
│   ├── package.json, vite.config.ts, tailwind.config.js
│   └── src/
│       ├── api/                        # Typed fetch wrappers
│       ├── pages/                      # Dashboard, InvoiceGenerate, InvoiceList, etc.
│       ├── components/                 # Layout, MonthSelector, DataTable, FileUpload, etc.
│       └── utils/                      # German number formatting
├── data/
│   ├── templates/                      # invoice.html + invoice.css
│   ├── generated/{year}/              # Output PDFs
│   ├── categories/{category_id}/      # Provider invoice PDFs
│   └── imports/                        # Source XLSX files
├── docs/
│   ├── BLUEPRINT-Invoice-Manager.md
│   ├── implementation-plan.md          # This file
│   └── reference-docs/                 # Reference templates, invoices, XLSX files
└── tests/
```

---

## Implementation Phases

### Phase 0: Project Setup Files
**Goal:** Create persistent tracking files before any code.

- [x] Save this plan as `docs/implementation-plan.md` (with revision history)
- [x] Create `MEMORY.md` at auto-memory path for learnings, gotchas, decisions
- [x] Create `CLAUDE.md` in project root for project conventions

---

### Phase 1: Foundation — Database & API Skeleton ✅
**Goal:** Project scaffold, all 10 SQLAlchemy models, database init, FastAPI running.

**Files created:**
- [x] `pyproject.toml` — Dependencies + `[dependency-groups]` for dev deps
- [x] `.gitignore`, `.env.example`
- [x] `backend/config.py` — Pydantic Settings (DATA_DIR, DATABASE_URL)
- [x] `backend/database.py` — Engine with WAL mode + FK enforcement, SessionLocal, get_db
- [x] `backend/models/` — All 10 models (SQLAlchemy 2.0 `Mapped[]` + `mapped_column()`)
- [x] `backend/main.py` — FastAPI with lifespan, CORS, `/api/health`
- [x] `tests/conftest.py` — In-memory SQLite fixtures
- [x] `tests/test_foundation.py` — 6 tests (health, tables, CRUD, FK relationships)

**Verified:** 6/6 tests pass.

---

### Phase 2: Core Business Logic ✅
**Goal:** Working days, cost calculation, and formatting — the three services everything depends on.

**Files created:**
- [x] `backend/services/working_days.py` — `easter_date()`, `hessen_holidays()` (10 holidays incl. Fronleichnam), `working_days_in_month()`, `distribute_cost_by_working_days()` (Decimal/ROUND_HALF_UP, remainder to last month)
- [x] `backend/services/formatting.py` — `format_eur()` (German: `1.234,56 €`), `round_currency()`, `format_date_german()`, `format_period()`, `format_month_year()`, `invoice_number()`, `invoice_filename()`
- [x] `backend/services/cost_calculation.py` — `ResolvedLineItem` + `InvoicePreview` dataclasses, `calculate_fixed_amount()`, `calculate_direct_amount()` (EUR vs USD), `calculate_distributed_amount()`, `calculate_upwork_amount()`, `resolve_line_items()` orchestrator with net/VAT/gross
- [x] `tests/test_business_logic.py` — 56 tests

**Key details:**
- 2025 working days verified: Jan=22, Feb=20, Mar=21, Apr=20, May=20, Jun=19, Jul=23, Aug=21, Sep=22, Oct=22, Nov=20, Dec=21 (Total=251)
- Kaletsch Q1 distribution (8295.00): Jan=2896.67, Feb=2633.33, Mar=2765.00 (sum = 8295.00 exactly)
- Note: algorithmic distribution differs from historical invoice amounts (e.g. Jan pos4=2851.20 in tracking.json) — likely manual adjustments in original process

**Verified:** 56/56 tests pass (62 total with Phase 1).

---

### Phase 3: Data Import Pipelines + CRUD APIs ✅
**Goal:** Import Upwork XLSX, bank statements XLSX, provider invoices; full CRUD for all entities.

**Phase 3A — Import services:**
- [x] `backend/services/upwork_import.py`
  - Parse sheet "data" with 9 columns (Date, Transaction ID, Transaction type, Transaction summary details, Description 1, Ref ID, Amount in local currency, Currency, Payment method)
  - **Reuse regex from** `generate_invoice.py:404-431` for period parsing
  - Month assignment by period END date
  - Duplicate detection by tx_id
- [x] `backend/services/bank_import.py`
  - Parse 7 columns: Buchungstag, Wertstellung, Umsatzart, Buchungstext, Betrag, RK, Buchungsjahr
  - Auto-match categories by searching Buchungstext for `bank_keywords` (case-insensitive)
  - Extract invoice references (e.g., "ZAHLUNGSGRUND: INV320", "INVOICE  AEO000811") via regex
- [x] `backend/services/provider_invoice_service.py`
  - CRUD helpers + PDF file storage in `data/categories/{category_id}/`

**Phase 3B — Pydantic schemas + CRUD routers:**
- [x] `backend/schemas/` — Base/Create/Update/Response per entity (8 schema modules)
- [x] `backend/routers/` — REST endpoints for all entities + import endpoints (9 routers)

**Key API endpoints:**

| Method | Path | Purpose |
|--------|------|---------|
| CRUD | `/api/clients[/{id}]` | Client management |
| CRUD | `/api/cost-categories[/{id}]` | Category management |
| CRUD | `/api/line-item-definitions[/{id}]` | Line item config |
| CRUD | `/api/provider-invoices[/{id}]` | Provider invoices + PDF upload/download |
| POST | `/api/bank-transactions/import` | Import bank XLSX |
| POST | `/api/upwork-transactions/import` | Import Upwork XLSX |
| CRUD | `/api/payments[/{id}]` | Payment receipts |
| GET | `/api/working-days/{year}/{month}` | Working day count |

**Verified:** 120/120 tests pass (62 from Phase 1-2 + 58 new: 30 import service tests + 28 API CRUD tests).

---

### Phase 4: Invoice Generation Engine + PDF
**Goal:** Preview, generate, and render invoices as HTML-to-PDF.

**Files to create:**
- `backend/services/invoice_engine.py`
  - `preview_invoice(client_id, year, month, db)` — Dry-run: resolve amounts, calculate net/VAT/gross, return warnings
  - `generate_invoice(request, db)` — Full workflow: resolve, apply overrides, render, store, link transactions
  - VAT = round(net x 0.19, ROUND_HALF_UP)
- `backend/services/invoice_renderer.py`
  - Jinja2 HTML template rendering
  - WeasyPrint HTML-to-PDF conversion
- `data/templates/invoice.html` + `invoice.css`
  - Match reference layout: A4, Helvetica Neue Light, 3-column table (Pos, Bezeichnung, Betrag)
  - Header: logo, 29ventures GmbH address, client address, invoice number, period, date
  - Summary: Netto, USt. 19%, Brutto
  - Footer: bank details, company registration
  - **Reference:** Extract exact layout from `AR202506-02.docx`
- `backend/routers/invoices.py`
  - `POST /api/invoices/preview` — Dry-run
  - `POST /api/invoices` — Generate + store
  - `GET /api/invoices/{id}/download` — PDF download
  - `PATCH /api/invoices/{id}/status` — Update status
  - `GET /api/invoices` — List with filters

**Verify:** Generate Jan 2025 invoice -> amounts match validation data (net 35,535.80, VAT 6,751.80, gross 42,287.60). PDF renders correctly.

---

### Phase 5: Seed Data + Validation
**Goal:** Load all historical data, validate system produces correct amounts for Jan-Jun 2025.

**Files to create:**
- `backend/seed/seed_data.py` — All constants from `tracking.json` and blueprint section 8
  - Client: DRS Holding AG (Am Sandtorkai 58, 20457 Hamburg)
  - 4 cost categories with bank_keywords
  - 6+1 line item definitions
  - Junior FM invoices: 12 months from tracking.json
  - Kaletsch invoices: 4 quarterly with bank payments from tracking.json
  - Aeologic invoices: 13 with drs_month_mapping from tracking.json (Jan + Apr marked as unclear)
  - Working days config: DE/HE
- `backend/seed/loader.py` — Idempotent loading with `python -m backend.seed.loader`
- `tests/test_seed_validation.py` — Parametrized test for all 6 months:

  | Month | Net | VAT | Gross |
  |-------|-----|-----|-------|
  | Jan 2025 | 35,535.80 | 6,751.80 | 42,287.60 |
  | Feb 2025 | 36,666.09 | 6,966.56 | 43,632.65 |
  | Mar 2025 | 38,524.74 | 7,319.70 | 45,844.44 |
  | Apr 2025 | 41,724.12 | 7,927.58 | 49,651.70 |
  | May 2025 | 39,468.65 | 7,499.04 | 46,967.69 |
  | Jun 2025 | 36,587.69 | 6,951.66 | 43,539.35 |

**Note:** Aeologic months Jan 2025 (1,551.41) and Apr 2025 (8,238.89) have unclear source mappings (noted in tracking.json). Seed these as manual assignments for now; user will verify later.

---

### Phase 6: React Frontend
**Goal:** Full UI for all workflows.

**Phase 6A — Scaffold + core pages:**
- Vite + React + Tailwind + React Router
- `vite.config.ts` with proxy `/api` -> `localhost:8000`
- `Layout.tsx` — Sidebar navigation (Dashboard, Invoices, Categories, Provider Invoices, Bank, Upwork, Payments, Settings)
- `Dashboard.tsx` — Monthly overview with status cards per category
- `InvoiceGenerate.tsx` — Month/client selector -> preview -> override -> invoice number + date inputs -> generate -> download PDF
- `InvoiceList.tsx` — Table of generated invoices with status, download, status update

**Phase 6B — Data management pages:**
- `CostCategories.tsx` + `CostCategoryDetail.tsx` — CRUD with bank keywords tag input
- `ProviderInvoices.tsx` — Category-first upload, PDF upload, metadata entry
- `BankTransactions.tsx` — XLSX import with preview, auto-matched categories, manual assignment
- `UpworkTransactions.tsx` — XLSX import with preview, month assignments
- `Payments.tsx` — Record incoming payments, match to invoices
- `Settings.tsx` — Client config, line item definitions

**Reusable components:** `MonthSelector`, `AmountDisplay` (German format), `StatusBadge`, `FileUpload`, `DataTable`, `ConfirmDialog`

---

### Phase 7: MCP Server
**Goal:** 10 query tools + 7 action tools + 3 resources.

- `mcp_server/server.py` — FastMCP entry point, shares SQLAlchemy models + services with backend
- **Query tools:** get_invoice_status, get_month_overview, get_open_invoices, get_category_costs, get_reconciliation, get_missing_data, get_upwork_summary, search_transactions, get_working_days, get_distribution
- **Action tools:** generate_invoice, import_upwork_xlsx, import_bank_statement, record_provider_invoice, link_bank_payment, record_payment, update_invoice_status
- **Resources:** invoices://overview/{month}, invoices://client/{id}, invoices://category/{id}

**Verify:** `mcp dev mcp_server/server.py`, test each tool via MCP inspector.

---

### Phase 8: Polish + Dashboard + Reconciliation
**Goal:** Error handling, reconciliation views, final quality.

- Dashboard aggregation: `GET /api/dashboard/monthly/{year}/{month}`, `/open-invoices`, `/reconciliation/{year}/{month}`
- Reconciliation service: provider invoices vs bank payments, generated invoices vs client payments
- Input validation, error handling, file type/size limits
- Invoice re-generation with version archival
- Frontend: loading states, empty states, error boundaries

---

## Critical Path

```
Phase 1 (Foundation) -> Phase 2 (Business Logic) -> Phase 3 (Imports + CRUD) -> Phase 4 (Invoice Engine) -> Phase 5 (Seed + Validation)
                                                                                      |
                                                         Phase 6 (Frontend) / Phase 7 (MCP) / Phase 8 (Polish)
```

Phase 2 (working days + cost calculation) is the single most critical component — every downstream feature depends on correct numbers. Phase 5 (seed validation) is the acceptance gate.

---

## Key Risks

| Risk | Mitigation |
|------|------------|
| WeasyPrint system deps on macOS | `brew install pango cairo libffi` early in setup |
| Aeologic month mapping unclear for Jan + Apr 2025 | Seed with best-guess assignments; user verifies later |
| Working day distribution may not exactly match historical amounts | Implement algorithm from existing `generate_invoice.py`; accept minor rounding differences |
| Upwork/bank XLSX format changes | Build parsers against actual sample files; validate on import |

---

## Verification Plan

1. **Unit tests:** Working days, formatting, cost calculation (each cost type)
2. **Integration tests:** Seed data -> preview_invoice -> validate all 6 months match expected amounts
3. **Import tests:** Parse actual Upwork + bank XLSX files, verify against tracking.json
4. **PDF output:** Generate Jan 2025 invoice, compare visually to reference AR202501-02.docx
5. **MCP tools:** Test each tool via `mcp dev`, verify query results match API
6. **End-to-end:** Full workflow: import data -> generate invoice -> download PDF -> record payment -> dashboard shows correct status
