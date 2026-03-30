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
- `docs/` — Blueprint, implementation plan, architecture, memory, reference docs
- `tests/` — pytest test suite

## Development Commands
```bash
# Backend
uv run uvicorn backend.main:app --reload --port 8000

# Frontend
cd frontend && npm run dev

# Tests
uv run pytest

# Database migrations
uv run alembic upgrade head           # Apply all pending migrations
uv run alembic revision --autogenerate -m "description"  # Create new migration after model changes
uv run alembic stamp head             # Stamp existing DB (first time only)

# Seed data
uv run python -m backend.seed.loader

# MCP server
uv run python -m mcp_server.server
```

## Conventions
- SQLAlchemy 2.0 style: `Mapped[]` + `mapped_column()`
- All monetary calculations: `Decimal` with `ROUND_HALF_UP` to 2 decimal places
- German number formatting: `1.234,56 EUR` (period=thousands, comma=decimal)
- Date formatting: `DD.MM.YYYY` (German) on invoices, ISO `YYYY-MM-DD` in API/DB
- API prefix: `/api/`
- Soft-delete for clients and cost categories (active boolean flag)
- File paths in DB are relative to DATA_DIR
- Invoice numbering: `YYYYMM-client_number` (e.g., `202501-02`). Filename prefix `AR` (e.g., `AR202501-02.pdf`). The `AR` prefix appears only in the filename, NOT in the invoice text.

## Documentation Protocol

Three living documents in `docs/` — read and update them at phase boundaries:

| Document | Purpose |
|----------|---------|
| [`docs/implementation-plan.md`](docs/implementation-plan.md) | The plan with phase details and revision log. Source of truth for what's done and what's next. |
| [`docs/architecture.md`](docs/architecture.md) | Business domain, data model, cost types, validation baseline, architecture decisions. Updated as the app evolves. |
| [`docs/memory.md`](docs/memory.md) | Known gotchas, German terminology, accumulated learnings. Keep under 100 lines; for deep topics create `docs/memory-{topic}.md` and link to it. |

**Before starting an implementation phase:**

1. Read `docs/implementation-plan.md` — understand what's planned
2. Read `docs/memory.md` — recall gotchas and prior decisions
3. Read `docs/architecture.md` — understand current system state
4. If scope changed or new insights exist, update the plan and add a revision entry explaining what changed and why

**After completing an implementation phase:**

1. Update `docs/implementation-plan.md`:
   - Check off completed items `[x]`
   - Update the phase status in the Phase Overview table
   - Add a revision entry using the template in the revision log — document scope changes, decisions made, lessons learned, and any plan adjustments for upcoming phases
2. Update `docs/memory.md` — capture new findings, gotchas, decisions. Add a revision entry noting what was added/changed.
3. Update `docs/architecture.md` — reflect new components and connections. Add a revision entry noting structural changes.

All three docs have a Revision Log section at the top — always append to it when making changes.

**When encountering findings mid-implementation:**

- Immediately note gotchas, unexpected behaviors, or decisions in `docs/memory.md`

## Reference Data
- `docs/reference-docs/invoice_data/generate_invoice.py` — Working business logic to reference (working days, distribution, Upwork parsing, EUR formatting)
- `docs/reference-docs/invoice_data/tracking.json` — Historical validation data for all 6 months + Aeologic month mapping
- `docs/reference-docs/invoice_data/config.json` — Client/invoice config
- `docs/reference-docs/AR202506-02.docx` — Reference invoice template (layout to match)
- `docs/reference-docs/upwork-transactions_20260225.xlsx` — Sample Upwork export (214 transactions)
- `docs/reference-docs/Kontoumsätze Aeologic + Kaletsch.xlsx` — Sample bank statement
