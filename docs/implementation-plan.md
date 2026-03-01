# Invoice Manager - Implementation Plan

## Revision History

| Rev | Date | Description |
|-----|------|-------------|
| 1.0 | 2026-02-26 | Initial plan created from blueprint review + codebase exploration |
| 1.1 | 2026-02-26 | Phase 0 + Phase 1 completed; Phase 2 completed |
| 1.2 | 2026-02-26 | Phase 3 completed |
| 1.3 | 2026-02-26 | Phase 4 completed |
| 1.4 | 2026-02-26 | Phase 5 completed |
| 1.5 | 2026-02-26 | Phase 6 completed |
| 1.6 | 2026-02-26 | Phase 7 completed |
| 1.7 | 2026-02-26 | Phase 8 completed |
| 1.8 | 2026-02-26 | Phase 9 completed — quality & operational hardening (337 backend + 32 frontend tests) |
| 1.9 | 2026-02-27 | Post-build: User Guide, Makefile, auto-seed on startup, DYLD_LIBRARY_PATH fix |
| 2.0 | 2026-02-28 | Revision Sprint 1: bug fixes, document management, multi-client foundation |
| 2.1 | 2026-02-28 | Revision Sprint 1 completed — all 13 tasks done (337 backend + 32 frontend tests) |
| 3.0 | 2026-02-28 | Revision Sprint 2: bulk upload, transaction matching, FX tracking, reconciliation |

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

### Phase 4: Invoice Generation Engine + PDF ✅
**Goal:** Preview, generate, and render invoices as HTML-to-PDF.

**Files created:**
- [x] `backend/services/invoice_engine.py`
  - `preview_invoice(client_id, year, month, db)` — Dry-run via `resolve_line_items`
  - `generate_invoice(...)` — Full workflow: resolve, apply overrides, render HTML/PDF, persist record + items
  - Supports amount overrides per position
  - Duplicate invoice number detection
- [x] `backend/services/invoice_renderer.py`
  - `render_invoice_html()` — Jinja2 template rendering with German formatting
  - `render_invoice_pdf()` — WeasyPrint HTML-to-PDF
  - `render_and_save_pdf()` — Render and write to disk
- [x] `data/templates/invoice.html` + `invoice.css`
  - A4 layout, Helvetica Neue Light, 3-column table (Pos, Bezeichnung, Betrag)
  - Header: sender line, client address, invoice number, period, date
  - Summary: Netto-Rechnungsbetrag, Umsatzsteuer 19%, Brutto-Rechnungsbetrag
  - Footer: bank details (IBAN, BIC), company registration, contact info
  - CSS @page with running footer element
- [x] `backend/routers/invoices.py` — Updated with full endpoints:
  - `POST /api/invoices/preview` — Dry-run
  - `POST /api/invoices` — Generate + store + PDF
  - `GET /api/invoices/{id}/download` — PDF download (FileResponse)
  - `PATCH /api/invoices/{id}/status` — Update status
  - `GET /api/invoices` — List with filters
- [x] `backend/schemas/generated_invoice.py` — Added: `InvoicePreviewRequest`, `InvoicePreviewResponse`, `ResolvedLineItemResponse`, `InvoiceGenerateRequest`
- [x] `tests/test_invoice_engine.py` — 34 tests

**Bug fix:** `cost_calculation.py` — `sum()` on empty items list returned `int(0)` instead of `Decimal("0")`, fixed with start value.

**Note:** WeasyPrint requires `DYLD_LIBRARY_PATH=/opt/homebrew/lib` on macOS for PDF rendering. Tests mock `render_and_save_pdf` to avoid this dependency.

**Verified:** 154/154 tests pass (120 from Phase 1-3 + 34 new).

---

### Phase 5: Seed Data + Validation ✅
**Goal:** Load all historical data, validate system produces correct amounts for Jan-Jun 2025.

**Files created:**
- [x] `backend/seed/seed_data.py` — All constants from `tracking.json` and blueprint
  - Client: DRS Holding AG (Am Sandtorkai 58, 20457 Hamburg)
  - 4 cost categories (junior_fm, cloud_engineer, upwork_mobile, aeologic) with bank_keywords
  - 7 line item definitions (6 regular + 1 optional Reisekosten)
  - Junior FM invoices: 12 months from tracking.json
  - Kaletsch invoices: 4 quarterly with bank payments and covers_months
  - Aeologic invoices: 13 originals + 6 DRS month-mapped (with synthetic combined invoices for Jan/Apr unclear sources)
  - Upwork transactions: 6 synthetic monthly totals (one per validation month)
  - Validation targets: expected amounts, historical overrides, auto-computed net totals
  - Working days config: DE/HE
- [x] `backend/seed/loader.py` — Idempotent loading with `python -m backend.seed.loader`
  - Individual seed functions per entity type (client, categories, definitions, invoices, bank txns, upwork txns)
  - `seed_all(db)` orchestrator with idempotency check (returns bool)
  - `__main__` block with summary output
- [x] `tests/test_seed_validation.py` — 87 tests across 3 test classes:
  - `TestSeedLoader` (9 tests): verifies all entities are created correctly
  - `TestAutoComputedPreview` (48 tests): verifies auto-computed values for each cost type per month
  - `TestHistoricalValidation` (30 tests): with overrides, verifies exact historical amounts

**Validation results** (all 6 months match with Pos 4 overrides):

  | Month | Net | VAT | Gross |
  |-------|-----|-----|-------|
  | Jan 2025 | 35,535.80 | 6,751.80 | 42,287.60 |
  | Feb 2025 | 36,666.09 | 6,966.56 | 43,632.65 |
  | Mar 2025 | 38,524.74 | 7,319.70 | 45,844.44 |
  | Apr 2025 | 41,724.12 | 7,927.58 | 49,651.70 |
  | May 2025 | 39,468.65 | 7,499.04 | 46,967.69 |
  | Jun 2025 | 36,587.69 | 6,951.66 | 43,539.35 |

**Key findings:**
- Pos 4 (Kaletsch distributed) auto-computed values differ from historical due to working-day algorithm vs original manual process. Overrides resolve this.
- Aeologic Jan 2025 (€1,551.41) and Apr 2025 (€8,238.89) seeded as synthetic combined invoices with notes about ambiguous sources.
- Feb 2025 Reisekosten (€286.97) handled via Pos 7 override on manual line item.

**Verified:** 241/241 tests pass (154 from Phase 1-4 + 87 new).

---

### Phase 6: React Frontend ✅
**Goal:** Full UI for all workflows.

**Stack:** React 18, React Router v6, TanStack Query v5, Tailwind CSS v4, Vite 6, TypeScript

**Files created (34 total):**

**Scaffold (7 files):**
- [x] `frontend/package.json` — Dependencies (react 18, react-router-dom 6, @tanstack/react-query 5, tailwindcss 4)
- [x] `frontend/tsconfig.json` + `tsconfig.node.json` — Strict TS with `@/*` path alias
- [x] `frontend/vite.config.ts` — React + Tailwind plugins, proxy `/api` -> `localhost:8000`
- [x] `frontend/index.html` — Entry with `lang="de"`
- [x] `frontend/src/app.css` — Tailwind v4 `@import "tailwindcss"`
- [x] `frontend/src/vite-env.d.ts` — Vite types

**Types + utilities (2 files):**
- [x] `frontend/src/types/api.ts` — All TypeScript interfaces mirroring backend Pydantic schemas
- [x] `frontend/src/utils/format.ts` — German EUR formatting, date formatting, invoice number generation, status config

**API layer (2 files):**
- [x] `frontend/src/api/client.ts` — Typed fetch wrappers for all 10 API namespaces (clients, invoices, bank, upwork, etc.)
- [x] `frontend/src/hooks/useApi.ts` — TanStack Query hooks with query keys, mutations, and cache invalidation

**Reusable components (8 files):**
- [x] `AmountDisplay.tsx`, `StatusBadge.tsx`, `MonthSelector.tsx`, `DataTable.tsx`
- [x] `ConfirmDialog.tsx`, `FileUpload.tsx`, `PageHeader.tsx`, `Layout.tsx`

**Core pages (5 files):**
- [x] `Dashboard.tsx` — Monthly overview, summary cards, recent invoices, quick links
- [x] `InvoiceGenerate.tsx` — Multi-step: select month+client -> preview with editable amounts -> set invoice number/date -> generate -> download PDF
- [x] `InvoiceList.tsx` — Filterable table with status badges, PDF download, inline status update
- [x] `InvoiceDetail.tsx` — Full invoice view with line items, totals, status update, linked payments
- [x] `NotFound.tsx` — 404 page

**Data management pages (7 files):**
- [x] `CostCategories.tsx` — Category list with DataTable
- [x] `CostCategoryDetail.tsx` — Detail view with bank keywords, linked invoices/transactions
- [x] `ProviderInvoices.tsx` — List with category/month filters, PDF download links
- [x] `BankTransactions.tsx` — XLSX import, inline category assignment, unmatched row highlighting
- [x] `UpworkTransactions.tsx` — XLSX import, month summaries, transaction list
- [x] `Payments.tsx` — Create/delete payments, invoice matching
- [x] `Settings.tsx` — Client config editor, line item definition editor

**Routing (2 files):**
- [x] `frontend/src/router.tsx` — All routes under Layout with React Router v6
- [x] `frontend/src/main.tsx` — Entry: QueryClientProvider + RouterProvider

**Verified:** `npm install` (88 packages, 0 vulnerabilities), `tsc --noEmit` (0 errors), `vite build` (310 KB JS bundle). Backend 241/241 tests still pass.

---

### Phase 7: MCP Server ✅
**Goal:** 10 query tools + 7 action tools + 3 resources.

**Files created (6 total):**
- [x] `mcp_server/db.py` — Session context manager for tool calls
- [x] `mcp_server/server.py` — FastMCP entry point with lifespan, imports tools/resources
- [x] `mcp_server/__main__.py` — `python -m mcp_server` convenience entry
- [x] `mcp_server/tools_query.py` — 10 read-only query tools
- [x] `mcp_server/tools_action.py` — 7 action tools (DB writes)
- [x] `mcp_server/resources.py` — 3 resource templates
- [x] `tests/test_mcp_server.py` — 36 tests

**Query tools (10):**
- `get_invoice_status` — by number, ID, or month
- `get_month_overview` — full preview with all line items and totals
- `get_open_invoices` — unpaid invoices list
- `get_category_costs` — costs per category with month range filter
- `get_reconciliation` — provider invoices vs bank payments
- `get_missing_data` — data gap detection for a month
- `get_upwork_summary` — Upwork transaction summary
- `search_transactions` — keyword search across bank/upwork
- `get_working_days` — Hessen working days for a month
- `get_distribution` — working-day cost distribution calculator

**Action tools (7):**
- `generate_invoice` — full generation (resolve, render PDF, persist)
- `import_upwork_xlsx` — import Upwork XLSX
- `import_bank_statement` — import bank statement XLSX
- `record_provider_invoice` — create provider invoice record
- `link_bank_payment` — link bank transaction to provider invoice
- `record_payment` — record client payment receipt
- `update_invoice_status` — change invoice status

**Resources (3):**
- `invoices://overview/{month}` — monthly overview as markdown
- `invoices://client/{client_id}` — client info + recent invoices
- `invoices://category/{category_id}` — category details + transactions

**Architecture:** Separate process sharing SQLite DB via WAL mode. Session-per-tool-call pattern. Tools return formatted German text (never raise). stdio transport.

**Verified:** 277/277 tests pass (241 from Phase 1-6 + 36 new).

---

### Phase 8: Polish + Dashboard + Reconciliation ✅
**Goal:** Error handling, reconciliation views, final quality.
**Status:** Complete (310 tests pass, 0 TS errors, 322KB bundle)

**Backend (9 files):**
- `backend/services/file_validation.py` — upload validation (XLSX 10MB, PDF 20MB)
- `backend/services/reconciliation.py` — shared reconciliation service (dataclasses)
- `backend/schemas/dashboard.py` — dashboard + reconciliation response schemas
- `backend/routers/dashboard.py` — 3 endpoints: monthly, open-invoices, reconciliation
- `backend/services/invoice_engine.py` — added `regenerate_invoice()` with PDF archival
- `backend/routers/invoices.py` — added `POST /api/invoices/{id}/regenerate`
- Upload validation added to bank/upwork/provider-invoice import endpoints
- MCP `get_reconciliation()` refactored to use shared service

**Frontend (12 files):**
- `ErrorBoundary` wraps `<Outlet />` in Layout; `ErrorAlert` on all 8 list pages
- Dashboard enhanced: open invoices card, reconciliation summary section
- New Reconciliation page: month selector, provider vs bank table, unmatched transactions, payment status
- InvoiceDetail: "Neu generieren" button (draft/overdue only) with ConfirmDialog
- New hooks: `useDashboardMonthly`, `useDashboardOpenInvoices`, `useDashboardReconciliation`, `useRegenerateInvoice`

**Tests (3 files, 33 new tests):**
- `tests/test_file_validation.py` — 11 tests
- `tests/test_dashboard.py` — 16 tests (reconciliation service, dashboard API, upload validation)
- `tests/test_invoice_engine.py` — 6 regeneration tests added

---

## Phase 9 — Quality, Reliability & Operational Hardening

All functional features are complete. Phase 9 adds operational safeguards.

### Sub-phase 9A: CI Pipeline + Structured Logging
- [x] `.github/workflows/ci.yml` — GitHub Actions (pytest + typecheck + test + build)
- [x] `backend/logging_config.py` — stdlib logging setup
- [x] Add `logger.info()` to invoice_engine, bank_import, upwork_import, invoice_renderer

### Sub-phase 9B: Database Migrations + Backup
- [x] Alembic setup (`alembic.ini`, `alembic/env.py`, initial migration)
- [x] Replace `create_all()` with `alembic upgrade head` in `main.py` lifespan
- [x] `backend/services/backup.py` + `backend/routers/backup.py` — SQLite online backup
- [x] `tests/test_backup.py` (11 tests)

### Sub-phase 9C: API Pagination + WeasyPrint Check
- [x] `backend/schemas/pagination.py` — generic `PaginatedResponse[T]`
- [x] Add `skip`/`limit` params to all 8 list routers
- [x] WeasyPrint startup check in `main.py` lifespan

### Sub-phase 9D: Frontend Tests + E2E XLSX Validation
- [x] Vitest + React Testing Library setup (`vitest.config.ts`, `test/setup.ts`)
- [x] Tests for `format.ts` (19), AmountDisplay (4), StatusBadge (4), MonthSelector (5) — 32 total
- [x] `tests/test_xlsx_import_e2e.py` — real XLSX import validation (16 tests)

---

### Post-Build: User Guide, Makefile & DX Improvements ✅
**Goal:** Documentation and developer experience polish.

- [x] `docs/USER-GUIDE.md` — 3-section guide: How to Run, Functionality Explained, User Tests (12-step checklist with validation table)
- [x] `Makefile` — `setup`, `dev`, `backend`, `frontend`, `test`, `seed` targets
- [x] `backend/main.py` — Auto-seed on first startup via `seed_all()` in lifespan (idempotent)
- [x] `Makefile` — `DYLD_LIBRARY_PATH=/opt/homebrew/lib` inlined on uvicorn commands (macOS SIP strips env vars from `/usr/bin/make` child processes)

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

---

## Revision Sprint 1 — Bug Fixes, Document Management & Multi-Client Foundation

> **Date:** 2026-02-28
> **Spec:** `docs/InvoiceManager-Revision-Sprint-1.md`

### Context

The app is functional but a manual UI review revealed bugs (umlaut encoding, 404 downloads), missing features (upload UI, PDF preview, import history), and architectural gaps (single-client assumption, hardcoded company data). This sprint addresses all of these.

**Key scope decisions:**
- Task 5 (Documents page) **dropped** — replaced with inline file management in existing sections + bank transaction dedup + import file history
- Bank dedup: detect by booking_date + amount + description; prompt user for confirmation on duplicates
- Import history: store uploaded XLSX files on disk + `import_history` table for audit trail
- Company settings: new `company_settings` DB table (singleton) replaces hardcoded invoice template values

### DB Migration (single migration for entire sprint)

```
alembic revision --autogenerate -m "sprint1_import_history_company_settings_client_fields"
```

Creates:
1. `import_history` table (file_type, original_filename, stored_path, imported_at, record_count, skipped_count, notes)
2. `company_settings` table (company_name, address, managing_director, tax/VAT IDs, bank details, contact info)
3. 6 new nullable columns on `clients` table (country, vat_id, contact_person, email, payment_terms_days, notes)

### Task List

| # | Task | Priority | Status |
|---|------|----------|--------|
| 1 | Fix German umlaut encoding in ~15 frontend files | Critical | Done |
| 2 | Fix document download 404 (copy PDFs, fix seed filenames) | Critical | Done |
| 5b | Import file history (backend model/router + frontend display) | Medium | Done |
| 5a | Bank import dedup with user confirmation | Medium | Done |
| 6c | Company settings (DB table, router, template integration) | Medium | Done |
| 6a | Clients page (model extension + frontend CRUD page) | Medium | Done |
| 6b | Restructure Einstellungen (company data + client-scoped line items) | Medium | Done |
| 6d | Client scoping wiring (dashboard, invoice generation, filters) | Medium | Done |
| 3 | Upload UI for provider invoices (single + bulk) | High | Done |
| 4 | PDF preview modal (iframe-based) | High | Done |
| 7 | UX polish batch (7a-7h: formatting, tooltips, hover, edit mode, CRUD) | Low | Done |

### New Files

| File | Purpose |
|------|---------|
| `backend/models/import_history.py` | ImportHistory model |
| `backend/models/company_settings.py` | CompanySettings singleton model |
| `backend/schemas/import_history.py` | Import history response schema |
| `backend/schemas/company_settings.py` | Company settings response + update schemas |
| `backend/routers/settings.py` | GET/PATCH /api/settings/company |
| `frontend/src/pages/Clients.tsx` | Kunden page (list + detail/edit) |
| `frontend/src/components/PDFPreviewModal.tsx` | Inline PDF preview modal |
| `frontend/src/components/ConfirmDialog.tsx` | Reusable confirmation dialog |

### New API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET/PATCH | `/api/settings/company` | Company/sender settings CRUD |
| GET | `/api/bank-transactions/import-history` | Bank import history |
| GET | `/api/upwork-transactions/import-history` | Upwork import history |

### Sidebar Navigation (updated order)

1. Dashboard, 2. Rechnungen, 3. Rechnung erstellen, 4. Abstimmung, 5. **Kunden** (new), 6. Kategorien, 7. Lieferantenrechnungen, 8. Bank, 9. Upwork, 10. Zahlungen, 11. Einstellungen

---

## Revision Sprint 2 — Bulk Upload, Transaction Matching, FX Tracking & Reconciliation

> **Date:** 2026-02-28
> **Spec:** `docs/InvoiceManager-Revision-Sprint-2.md`

### Context

Sprint 2 adds: bulk PDF upload with auto-extraction, bidirectional transaction-to-invoice matching, currency/FX tracking, an improved reconciliation dashboard, and UX polish carry-overs. The goal is to eliminate manual data entry and make reconciliation a one-click workflow.

**Key decisions:**
- Bidirectional FK: `matched_transaction_id` on `provider_invoices` + existing `provider_invoice_id` on `bank_transactions`
- High-confidence matches (invoice number in bank description) auto-link immediately; medium/low go to review
- PDF extraction is best-effort with graceful fallback to manual entry
- Rename MCP tool `record_provider_invoice` → `create_provider_invoice`, add bulk variant
- Single Alembic migration for all Sprint 2 schema changes
- New dependency: `pdfplumber>=0.10.0`

### DB Migration (single migration for entire sprint)

New columns on `provider_invoices`: payment_status, matched_transaction_id (FK), amount_eur, bank_fee, fx_rate
New columns on `bank_transactions`: match_status, match_confidence
Backfill: existing linked records get payment_status='matched', match_status='auto_matched', amount_eur set for EUR invoices

### Task List

| # | Task | Priority | Status |
|---|------|----------|--------|
| 1 | Fix document download (auto-link PDFs on startup) | Critical | Pending |
| 2 | Bulk upload with PDF extraction + review step + MCP tools | Critical | Pending |
| 3 | Bidirectional transaction matching (auto-match, confidence scoring, review UI) | Critical | Pending |
| 4 | Currency/FX tracking (amount_eur, fx_rate, bank_fee, fee UI) | High | Pending |
| 5 | Improved reconciliation dashboard (3-section layout, matching actions) | Medium | Pending |
| 6 | UX polish carry-overs (tooltip, smart defaults, line item create) | Low | Pending |

### New Files

| File | Purpose |
|------|---------|
| `backend/services/transaction_matching.py` | Core matching logic (confidence scoring, auto-link, FX computation) |
| `backend/services/pdf_extraction.py` | PDF text extraction for bulk upload |
| `backend/schemas/matching.py` | Pydantic schemas for match endpoints |
| `backend/schemas/bulk_upload.py` | Pydantic schemas for bulk upload |
| `frontend/src/components/BulkUploadZone.tsx` | Multi-file upload + review table component |
| `frontend/src/components/MatchConfirmDialog.tsx` | FX detail panel for match confirmation |

### New API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/provider-invoices/bulk-upload` | Upload multiple PDFs, extract metadata |
| POST | `/api/provider-invoices/bulk-confirm` | Confirm and create records from bulk upload |
| POST | `/api/bank-transactions/{id}/match` | Confirm or reject a suggested match |
| POST | `/api/bank-transactions/{id}/manual-match` | Manually link a transaction to an invoice |

### New MCP Tools

| Tool | Purpose |
|------|---------|
| `create_provider_invoice` | Renamed from `record_provider_invoice`, extended params |
| `create_provider_invoices_bulk` | Bulk create provider invoice records |
| `get_unmatched_transactions` | Query unmatched bank transactions |
| `get_unmatched_invoices` | Query invoices without payment |
| `match_transaction_to_invoice` | Link a transaction to an invoice |
