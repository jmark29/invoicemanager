# Invoice Manager - Memory

## Revision Log

| Rev | Date | Description |
|-----|------|-------------|
| 1.0 | 2026-03-29 | Initial version — extracted from CLAUDE.md |
| 1.1 | 2026-03-30 | Added Sprint 2/3 learnings: PDF preview, reconciliation queries, icon system |
| 1.2 | 2026-03-30 | Added Sprint 4 learnings: DOCX parsing, running-balance, migration idempotency |

---

## Known Gotchas

- WeasyPrint requires system libs on macOS: `brew install pango cairo libffi`
- Upwork XLSX sheet name is `"data"` (not default "Sheet1")
- Bank XLSX Buchungstext contains invoice refs as `"ZAHLUNGSGRUND: INV320"` or `"INVOICE  AEO000811"` (note double space)
- Aeologic month mapping for Jan 2025 (1,551.41) and Apr 2025 (8,238.89) is unclear — tracked in `tracking.json` as "Nicht eindeutig zuordenbar"
- Upwork "Amount in local currency" is EUR despite the column name suggesting otherwise
- Use `uv` for Python package management (not pip directly, due to PEP 668 on macOS)
- PDF preview in iframes is unreliable (intermittent 503) — use blob URL approach (fetch + createObjectURL) instead
- Reconciliation queries must use OR(assigned_month, invoice_date) to capture invoices that lack `covers_months` (e.g., Aeologic)
- `pdfplumber` used for PDF text extraction in bulk upload — best-effort, graceful fallback to manual entry
- Sidebar icons use `lucide-react` SVG icons (not emoji) — installed in Sprint 3
- Company sender data lives in `company_settings` DB table (singleton), not hardcoded in templates
- Sprint 2 review doc is named `InvoiceManager-Revision-Sprint-3.md` (confusingly — it's the Sprint 2 *review* that became the Sprint 3 *spec*)
- Alembic migrations must handle pre-existing columns (from SQLAlchemy's create_all during app startup) — use `_column_exists()` PRAGMA check before `add_column`
- DOCX table for invoices has 4 columns but cols 1&2 are merged (same text) — `Bezeichnung` is in cells[1] or cells[2], `Betrag` is always cells[-1]
- Running-balance distributed costs: still use per-month working-day distribution, but check `invoice_line_item_sources` for already-invoiced portions. Full un-invoiced amount = sum of all months' portions.
- For USD provider invoices without `amount_eur`, fall back to `abs(bank_transaction.amount_eur)` — same logic as per-month resolver
- `python-docx>=1.1` installed via `uv` — pulls in `lxml` as dependency

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
