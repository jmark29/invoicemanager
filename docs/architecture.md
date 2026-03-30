# Invoice Manager - Architecture

## Revision Log

| Rev | Date | Description |
|-----|------|-------------|
| 1.0 | 2026-03-29 | Initial version — extracted from CLAUDE.md |
| 1.1 | 2026-03-30 | Added Sprint 2/3 changes: FX tracking, transaction matching, bulk upload, PDF extraction |
| 1.2 | 2026-03-30 | Added Sprint 4: invoice import, running-balance reconciliation, invoice_line_item_sources |

---

## Business Domain — 4 Cost Types

Every variable line item on the invoice is resolved through one of these cost types:

| Cost Type | Example | Logic |
|-----------|---------|-------|
| `fixed` | Pos 1, 2 (PM, Senior FM) | Constant amount from `line_item_definitions.fixed_amount` |
| `direct` | Pos 3 (Junior FM), Pos 6 (Aeologic) | 1:1 pass-through of provider invoice. EUR: use invoice amount. USD: use EUR bank debit amount (includes FX + fees) |
| `distributed` | Pos 4 (Kaletsch/Cloud Engineer) | Quarterly invoice distributed across 3 months by Hessen working days. Base = bank payment (invoice + bank fee). Last month gets remainder. |
| `upwork` | Pos 5 (Mobile Dev) | Sum of Upwork XLSX transactions assigned to the month. Assignment rule: period END date determines month. |

## Data Model — Key Relationships

```
clients --(1:N)--> line_item_definitions --(N:1)--> cost_categories
clients --(1:N)--> generated_invoices --(1:N)--> generated_invoice_items
cost_categories --(1:N)--> provider_invoices --(1:1?)--> bank_transactions (bidirectional FK)
cost_categories --(1:N)--> upwork_transactions
generated_invoices --(1:N)--> payment_receipts
company_settings (singleton) --> invoice template sender data
import_history --> audit trail for XLSX/PDF imports
```

- `provider_invoices.assigned_month` determines which billing month an invoice belongs to (defaults to invoice_date month, overridable)
- `bank_transactions.category_id` is auto-matched via `cost_categories.bank_keywords`
- `generated_invoice_items` links back to source data (provider_invoice_id, upwork_tx_ids_json) for traceability

### Sprint 2 Additions

- **Bidirectional matching:** `provider_invoices.matched_transaction_id` (FK to bank_transactions) + existing `bank_transactions.provider_invoice_id`. Confidence scoring: high (auto-link), medium/low (review queue).
- **FX tracking:** `provider_invoices.amount_eur`, `fx_rate`, `bank_fee` columns. For USD invoices, `amount_eur` = bank debit amount; `fx_rate` and `bank_fee` computed from difference.
- **Match status:** `bank_transactions.match_status` (unmatched/auto_matched/manual_matched), `bank_transactions.match_confidence`. `provider_invoices.payment_status` (unpaid/matched/paid).
- **Bulk upload:** `backend/services/pdf_extraction.py` uses `pdfplumber` to extract invoice number, date, amount, currency from PDFs. Best-effort with fallback to manual entry.
- **Transaction matching:** `backend/services/transaction_matching.py` — confidence scoring by searching bank description for invoice number patterns.

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

## Architecture Decisions

- **HTML-to-PDF over DOCX editing** — More maintainable, no XML run-splitting issues, HTML preview doubles as in-browser preview before generating
- **`assigned_month` on provider_invoices** — Added to blueprint; needed for irregular invoices (Aeologic) where invoice_date month doesn't always match the billing month
- **MCP server as separate process** — Shares SQLite DB file with FastAPI backend but runs independently; both use the same SQLAlchemy models and services
- **Bidirectional FK for matching** — Both `provider_invoices.matched_transaction_id` and `bank_transactions.provider_invoice_id` exist; enables querying from either direction
- **PDF preview via blob URL** — Fetch PDF as blob + createObjectURL instead of iframe src pointing at API endpoint; avoids intermittent 503 issues
- **Company settings as DB singleton** — Replaces hardcoded invoice template values; editable from Settings page
- **Lucide React icons** — Replaced emoji sidebar navigation with SVG icons for consistency and accessibility
- **Running-balance invoice generation** — Replaced per-month cost resolution with `resolve_line_items_running_balance()` that queries un-invoiced provider costs across ALL months. Old per-month `resolve_line_items()` kept as internal fallback.
- **`invoice_line_item_sources` table** — Many-to-many link between `generated_invoice_items` and `provider_invoices` with `amount_contributed`. Replaces single-FK traceability for new code paths. Old FK fields (`provider_invoice_id`, `distribution_source_id`) retained for backward compat.
- **Invoice import via DOCX parsing** — `python-docx` extracts invoice data from .docx files matching the 29ventures template. Line items auto-matched to `line_item_definitions` by position+description. Provider invoices auto-linked via `invoice_line_item_sources`.
- **Cost reconciliation (Kostenabgleich)** — Separate from bank Abstimmung. Tracks running balance per category: total provider costs - total invoiced = delta. Drill-down shows individual provider invoice linkage status.
