# InvoiceManager — Revision Sprint 2

> **Context:** This document continues from Sprint 1. The Invoice Manager is a React/TypeScript + FastAPI/Python + SQLite web application for 29ventures GmbH. Sprint 1 addressed Umlaut encoding, multi-client foundation, upload UI, preview modal, and various UX improvements. This sprint focuses on bulk document upload, intelligent transaction matching, currency/banking fee transparency, and completing items that were not fully resolved in Sprint 1.
> 
> **Stack:** React/TypeScript frontend (Vite, port 5173) + FastAPI/Python backend (port 8000) + SQLite database
> 
> **Date:** 2026-02-28
> 
> **Depends on:** `BLUEPRINT-Invoice-Manager.md` (canonical spec), `InvoiceManager-Revision-Sprint-1.md` (prior sprint)

---

## How to Use This Document

Tasks are ordered by priority and dependency. Task 1 is a Sprint 1 carry-over that must be fixed before the new features work correctly. Tasks 2–4 are the new bulk upload, matching, and currency features. Task 5 enhances the reconciliation dashboard. Task 6 covers remaining UX polish from Sprint 1.

The existing `BLUEPRINT-Invoice-Manager.md` remains the canonical reference for data model and business rules. This document describes the delta.

---

## Task 1: Fix Document Download (404 Error) — Sprint 1 Carry-Over

**Priority:** Critical — blocks preview (Task 4 from Sprint 1) and all document-related features in this sprint

### Current Behavior

`GET /api/provider-invoices/{id}/download` returns HTTP 404 with `{"detail":"PDF file not found"}`. The preview modal (which was built in Sprint 1) opens but shows a blank white area because it depends on this endpoint. The "Download" and "Herunterladen" buttons also fail silently.

### Root Cause

The database stores `file_path` values like `categories/junior_fm/ER2512-21.pdf`, but the backend's storage directory does not contain files at those paths. The original PDFs exist in provider-named folders on disk (e.g. `Junior FM/`, `Kaletsch - Cloud engineer/`, `Aeologic/`).

### What to Do

1. Find the backend's `UPLOAD_DIR` / `STORAGE_DIR` / `MEDIA_ROOT` configuration

2. **Option A (preferred):** Create the expected directory structure and copy or symlink the existing PDFs:
   
   ```
   {STORAGE_DIR}/categories/junior_fm/ER2501-19.pdf
   {STORAGE_DIR}/categories/junior_fm/ER2502-17.pdf
   ... (all 12 Junior FM invoices)
   {STORAGE_DIR}/categories/cloud_engineer/INV307.pdf
   ... (all Kaletsch quarterly invoices)
   {STORAGE_DIR}/categories/aeologic/AEO000716.pdf
   ... (all Aeologic invoices)
   ```

3. **Option B:** Update the `file_path` values in the database to match where the files actually are on disk

4. Add a startup validation that logs a warning for any `provider_invoice` where `file_path` is set but the file does not exist

5. Test downloading at least one file from each of the three categories

### Acceptance Criteria

- `GET /api/provider-invoices/{id}/download` returns the actual PDF with `Content-Type: application/pdf`
- The preview modal shows the PDF content (not a blank white area)
- The "Herunterladen" button in the preview modal triggers a file download
- Download works for Junior FM, Cloud Engineer, and Aeologic invoices

---

## Task 2: Bulk Upload with Auto-Record Creation

**Priority:** Critical — core new feature for this sprint

### Overview

Users need to upload multiple provider invoice PDFs at once. The system should create `provider_invoice` records automatically by extracting metadata from the PDFs. There are two ingestion paths:

**Path A — Direct PDF Upload:** User drops one or more PDFs onto the upload zone. The system extracts text from each PDF and parses invoice number, date, amount, and currency.

**Path B — MCP Data Entry:** An AI assistant (e.g. Claude Cowork) reads the invoices and pushes structured data via the MCP server API. This is the fallback when PDFs are not machine-readable.

### 2a. Bulk Upload UI

Add a bulk upload zone to the **Lieferantenrechnungen** page (above the table):

```
┌─────────────────────────────────────────────────┐
│                                                 │
│   📄 PDFs hierher ziehen oder klicken           │
│      Rechnungen werden automatisch erkannt      │
│                                                 │
└─────────────────────────────────────────────────┘
```

**Upload flow:**

1. User drops one or more PDF files (or clicks to open file picker)
2. For each file, the backend:
   a. Stores the PDF in `{STORAGE_DIR}/categories/{category_id}/` (or an `inbox/` folder if category unknown)
   b. Extracts text from the PDF using a Python library (e.g. `pdfplumber`, `PyPDF2`, or `pdfminer`)
   c. Attempts to parse: invoice number, invoice date, total amount, currency
   d. Attempts to match the provider to a `cost_category` using provider name or known patterns
3. Returns a list of extracted records for user review

**Review step (critical):**

After upload, show a confirmation table:

| Datei          | Erkannte Nr. | Datum      | Betrag   | Währung | Kategorie | Status            |
| -------------- | ------------ | ---------- | -------- | ------- | --------- | ----------------- |
| AEO000852.pdf  | AEO000852    | 30.12.2025 | 1,302.00 | USD     | aeologic  | ✅ Erkannt         |
| ER2512-21.pdf  | 12/2025      | 21.12.2025 | 1,600.00 | EUR     | junior_fm | ✅ Erkannt         |
| invoice_q4.pdf | —            | —          | —        | —       | —         | ⚠️ Manuell prüfen |

Each row is editable. User can correct any field before confirming. "Übernehmen" button creates all records at once.

### 2b. PDF Text Extraction Backend

Add endpoint: `POST /api/provider-invoices/bulk-upload`

- Accepts `multipart/form-data` with multiple PDF files
- For each file:
  1. Extract text using `pdfplumber` (preferred — handles tables well) or `PyPDF2`
  2. Parse with regex patterns per known provider format:
     - **Aeologic:** Look for `Invoice #: AEO\d+`, date format `DD/MM/YYYY` or `Month DD, YYYY`, amount after `Total Due` or `Amount Due`, currency `USD`
     - **Junior FM (Mikhail Iakovlev):** Look for invoice number pattern `\d{2}/\d{4}`, date in `DD.MM.YYYY` format, amount with EUR
     - **Kaletsch (Cloud Engineer):** Look for `INV\d+`, quarterly amounts, ZAR or EUR amounts
  3. Match to category by searching extracted text for each category's `bank_keywords`
  4. Return extracted data as JSON (not yet persisted)

Add endpoint: `POST /api/provider-invoices/bulk-confirm`

- Accepts the reviewed/corrected array of invoice records
- Creates `provider_invoice` records in the database
- Links uploaded files by setting `file_path`

### 2c. MCP Endpoint for AI-Assisted Data Entry

Ensure the MCP server exposes a tool that allows an AI assistant to create provider invoice records:

```
Tool: create_provider_invoice
Parameters:
  - category_id: string (required)
  - invoice_number: string (required)
  - invoice_date: string (YYYY-MM-DD, required)
  - amount: number (required)
  - currency: string (EUR/USD, required)
  - hours: number (optional)
  - hourly_rate: number (optional)
  - period_start: string (optional)
  - period_end: string (optional)
  - covers_months: string[] (optional)
  - notes: string (optional)
```

This allows the workflow: user feeds invoice PDFs to Claude Cowork → Claude reads them → Claude calls the MCP tool to push structured data into the Invoice Manager.

Also add a bulk variant:

```
Tool: create_provider_invoices_bulk
Parameters:
  - invoices: array of create_provider_invoice parameters
```

### 2d. Bulk Upload on Category Detail Page

On the Kategorie-Detail page (e.g. `/categories/junior_fm`), add a drop zone above the invoice table:

```
┌─────────────────────────────────────────────────┐
│  📄 PDFs für Junior FileMaker Entwickler        │
│     hierher ziehen oder klicken                 │
└─────────────────────────────────────────────────┘
```

This is category-scoped: all uploaded files are automatically assigned to that category. The same review step applies, but the category column is pre-filled and locked.

### Acceptance Criteria

- User can drop multiple PDFs on the Lieferantenrechnungen page
- System extracts invoice data and shows a review table
- User can correct any field before confirming
- Confirmed records are created in the database with linked PDF files
- MCP tools exist for AI-assisted invoice creation
- Category detail page has a category-scoped upload zone

---

## Task 3: Bidirectional Transaction Matching

**Priority:** Critical — core reconciliation feature

### Overview

The system must handle two scenarios:

**Scenario A — Transaction first, invoice later:** A bank transaction is imported (e.g. via XLSX). The system auto-matches it to a cost category via `bank_keywords`. Later, when the provider invoice is uploaded, the system links the invoice to the transaction.

**Scenario B — Invoice first, transaction later:** A provider invoice is uploaded/created. It sits as "unbezahlt" (unpaid). When bank data is imported, the system finds the matching transaction and links it.

### 3a. Enhanced Auto-Matching on Bank Import

When bank transactions are imported via `POST /api/bank-transactions/import`:

1. **Category matching (existing):** Search `description` for each category's `bank_keywords` → set `category_id`
2. **Invoice matching (new):** For each matched transaction, search for unlinked `provider_invoices` in the same category where:
   - The invoice number appears in the transaction `description` (e.g. "INVOICE AEO000852" contains "AEO000852")
   - OR the invoice amount (or EUR equivalent) is close to the transaction amount (within a configurable tolerance, e.g. 5% for FX transactions, exact for EUR)
   - OR the invoice date is within a reasonable window (±30 days) of the transaction date
3. **Confidence scoring:** Rate each potential match:
   - Invoice number found in description → high confidence (auto-link)
   - Amount match + date proximity → medium confidence (suggest, require confirmation)
   - Category match only → low confidence (show as candidate)
4. **Set match status** on the transaction:
   - `match_status`: `"auto_matched"`, `"suggested"`, `"manual"`, `"unmatched"`

### 3b. Enhanced Auto-Matching on Invoice Creation

When a new `provider_invoice` is created (via UI, bulk upload, or MCP):

1. Search `bank_transactions` for unlinked transactions in the same category
2. Apply the same matching logic (invoice number in description, amount proximity, date window)
3. If a high-confidence match is found, auto-link: set `bank_transactions.provider_invoice_id`
4. If medium-confidence matches exist, flag them for review

### 3c. Matching Review UI

On the **Abstimmung** (Reconciliation) page, add a section:

**"Offene Zuordnungen"** (Open Matches)

Show two sub-sections:

**Transaktionen ohne Rechnung** (Transactions without invoice):
| Datum | Beschreibung | Betrag | Kategorie | Vorgeschlagene Rechnung | Aktion |
|---|---|---|---|---|---|
| 30.12.2025 | INVOICE AEO000852... | -1.302,00 € | aeologic | AEO000852 (95% Match) | Bestätigen / Ablehnen |

**Rechnungen ohne Transaktion** (Invoices without transaction):
| Nr. | Kategorie | Datum | Betrag | Währung | Status |
|---|---|---|---|---|---|
| AEO000852 | aeologic | 30.12.2025 | 1,302.00 $ | USD | ⏳ Warte auf Zahlung |

**Actions:**

- "Bestätigen" → links the transaction to the invoice, calculates FX rate and bank fee
- "Ablehnen" → marks as rejected, removes suggestion
- "Manuell zuordnen" → opens a picker to select from all unlinked invoices/transactions

### 3d. Data Model Changes

Add columns to `bank_transactions` (if not already present):

```sql
ALTER TABLE bank_transactions ADD COLUMN match_status TEXT DEFAULT 'unmatched';
-- Values: 'auto_matched', 'suggested', 'manual', 'unmatched', 'rejected'

ALTER TABLE bank_transactions ADD COLUMN match_confidence REAL;
-- 0.0 to 1.0, used for sorting suggestions
```

Add columns to `provider_invoices` (if not already present):

```sql
ALTER TABLE provider_invoices ADD COLUMN payment_status TEXT DEFAULT 'unpaid';
-- Values: 'unpaid', 'matched', 'paid', 'partial'

ALTER TABLE provider_invoices ADD COLUMN matched_transaction_id INTEGER REFERENCES bank_transactions(id);
-- Reverse link for quick lookup

ALTER TABLE provider_invoices ADD COLUMN amount_eur REAL;
-- EUR equivalent (= original amount for EUR invoices, = bank debit for foreign currency)

ALTER TABLE provider_invoices ADD COLUMN bank_fee REAL;
-- Banking/FX fee component (see Task 4)

ALTER TABLE provider_invoices ADD COLUMN fx_rate REAL;
-- Effective exchange rate (see Task 4)
```

### Acceptance Criteria

- Importing bank data auto-matches transactions to existing invoices by invoice number
- Creating invoices auto-matches to existing unlinked transactions
- The Abstimmung page shows unmatched items from both directions
- Users can confirm, reject, or manually assign matches
- Match status is tracked and visible

---

## Task 4: Currency Conversion and Banking Fee Tracking

**Priority:** High — needed for accurate cost pass-through to clients

### Overview

For foreign currency providers (Aeologic in USD, Kaletsch in ZAR/EUR via South Africa), the bank transaction amount includes both the converted invoice amount and banking/transfer fees. The total bank debit is what gets passed through to the client (rolled into the service cost), but internally the system must track the breakdown for cost transparency.

### 4a. Fee Calculation Logic

When a `bank_transaction` is linked to a `provider_invoice`:

**For EUR invoices (e.g. Junior FM):**

- `amount_eur` on the invoice = invoice `amount` (no conversion)
- `bank_fee` = `abs(transaction.amount_eur)` - `invoice.amount` (usually 0 for SEPA, but can be non-zero for international EUR transfers)
- `fx_rate` = 1.0

**For USD invoices (e.g. Aeologic):**

- The bank transaction is in EUR (negative, e.g. -€1,276.43)
- The invoice amount is in USD (e.g. $1,302.00)
- `amount_eur` = `abs(transaction.amount_eur)` (the full bank debit — this is what gets billed to the client)
- To separate FX and fee, we need an approach. Since we don't know the exact exchange rate the bank used, we calculate:
  - `fx_rate` = `abs(transaction.amount_eur)` / `invoice.amount` (effective rate including fee)
  - `bank_fee` = estimated, or entered manually if the bank statement itemizes it
  - **Practical approach:** Store `amount_eur` (the total bank debit) as the primary number. The `bank_fee` field is optional and can be filled in if the user knows the exact fee (e.g. from a separate bank fee line item). If not known, it stays NULL and the full bank debit is treated as the service cost.

**For distributed invoices (e.g. Kaletsch quarterly):**

- The distribution base is the **bank payment amount** (`amount_eur`), not the invoice face value
- This ensures banking fees are distributed proportionally across the covered months
- Example: Invoice €8,553.60, bank debit €8,568.93 (includes ~€15 fee) → distribute €8,568.93 across 3 months by working days

### 4b. UI for Fee Tracking

When confirming a transaction-to-invoice match (from the Abstimmung page or the matching review), show a detail panel:

```
┌─────────────────────────────────────────────┐
│ Zuordnung: AEO000852 ↔ Transaktion #47     │
│                                             │
│ Rechnungsbetrag:     1.302,00 $  (USD)      │
│ Banktransaktion:    -1.276,43 €  (EUR)      │
│                                             │
│ Effektiver Kurs:     0,9804 €/$             │
│ Bankgebühr:          [_______] € (optional) │
│                                             │
│ → Weiterberechnung:  1.276,43 €             │
│   (Gesamter Bankbetrag wird an Kunde        │
│    weiterberechnet)                         │
│                                             │
│ [Bestätigen]  [Abbrechen]                   │
└─────────────────────────────────────────────┘
```

The key fields:

- **Rechnungsbetrag:** Original invoice amount in original currency
- **Banktransaktion:** EUR amount debited from the bank account
- **Effektiver Kurs:** Calculated automatically (`bank_amount / invoice_amount`)
- **Bankgebühr:** Optional manual entry — if the user knows the exact fee (from a separate bank line), they can enter it. Otherwise leave blank.
- **Weiterberechnung:** The amount that will be passed to the client invoice. This is always the full bank debit amount (`abs(transaction.amount_eur)`).

### 4c. Cost Breakdown Visibility

On the **Kategorie-Detail** page, add a summary section showing cost breakdown over time:

```
Kostenübersicht — Aeologic
─────────────────────────────────────────────
Monat     Rechnung (USD)  Bankbetrag (EUR)  Gebühr (EUR)
2025-12   1.302,00 $      1.276,43 €        —
2025-11   1.246,00 $      1.220,15 €        —
2025-10     812,00 $        795,23 €        —
─────────────────────────────────────────────
Gesamt    8.234,00 $      8.067,45 €        —
Ø Kurs    0,9797 €/$
```

This gives internal transparency into FX costs without exposing it on client invoices.

### 4d. Impact on Invoice Generation

When generating a client invoice:

- For `cost_type = "direct"` with foreign currency: use `provider_invoice.amount_eur` (the bank debit) as the line item amount
- For `cost_type = "distributed"`: use `provider_invoice.amount_eur` as the distribution base
- For `cost_type = "fixed"` and `cost_type = "upwork"`: no change (already in EUR)

This implements the user's decision to **roll banking fees into the service cost** — the client sees one combined EUR amount per category.

### Acceptance Criteria

- When linking a foreign currency invoice to a bank transaction, the system calculates the effective FX rate
- `amount_eur` stores the full bank debit for foreign currency invoices
- Banking fee can optionally be recorded
- Kategorie-Detail shows a cost breakdown over time for foreign currency categories
- Invoice generation uses `amount_eur` (bank debit) for cost pass-through
- Distributed costs use the bank payment amount as the distribution base

---

## Task 5: Improved Reconciliation Dashboard

**Priority:** Medium — enhances the existing Abstimmung page

### Current State

The Abstimmung page exists but has limited functionality. With the new matching logic from Task 3, it needs to become the central hub for financial reconciliation.

### What to Build

Restructure the Abstimmung page into three sections:

#### Section 1: Monatsübersicht (Monthly Overview)

Month/year selector (default to most recent month with data). Show summary cards:

| Card                  | Value                                      |
| --------------------- | ------------------------------------------ |
| Lieferantenrechnungen | Count and total EUR for the month          |
| Banktransaktionen     | Count and total EUR for the month          |
| Zugeordnet            | Count and total of matched pairs           |
| Offen                 | Count of unmatched items (both directions) |
| Differenz             | Sum of banking fees / FX differences       |

#### Section 2: Offene Zuordnungen (from Task 3c)

The matching review UI described in Task 3c lives here.

#### Section 3: Abgeschlossene Zuordnungen (Completed Matches)

Table showing all confirmed matches for the selected month:

| Rechnung  | Kategorie | Betrag (Original) | Banktransaktion | Betrag (EUR) | Gebühr | Status |
| --------- | --------- | ----------------- | --------------- | ------------ | ------ | ------ |
| 12/2025   | junior_fm | 1.600,00 €        | 21.12.2025      | -1.600,00 €  | 0,00 € | ✅      |
| AEO000852 | aeologic  | 1.302,00 $        | 30.12.2025      | -1.276,43 €  | —      | ✅      |

### Acceptance Criteria

- Abstimmung page shows monthly summary with match statistics
- Open matches are clearly visible with actions
- Completed matches show the full picture including FX and fees
- Month selector defaults to most recent month with data

---

## Task 6: UX Polish — Sprint 1 Carry-Overs

**Priority:** Low — individually small items that were not completed in Sprint 1

### 6a. Bank Description Tooltip

On the Banktransaktionen page, truncated descriptions (ending with `...`) should show the full text on hover. Use a `title` attribute or a styled tooltip component.

### 6b. Dashboard Smart Default

The Dashboard currently defaults to February 2026 (current month) showing all zeros. Instead:

- Default to the most recent month that has either generated invoices or provider invoice data
- If no data exists, show the current month with a helpful empty state

### 6c. Invoice Date Default

On "Rechnung erstellen", the Rechnungsdatum should default to the last day of the selected invoice month (e.g. selecting Juni 2025 → defaults to 30.06.2025), not today's date.

### 6d. Category Row Hover

On the Kostenkategorien list page, add a hover effect (background color change + cursor pointer) to indicate rows are clickable.

### 6e. Line Item Client Scoping

The Rechnungspositionen section in Einstellungen should have a client dropdown filter at the top. Line items should be scoped per client. When a new client is added, they start with zero line items.

### 6f. "Neue Position" Button

Add a button to the Rechnungspositionen table in Einstellungen to create new line item definitions. Currently there's only "Bearbeiten" on existing rows.

### Acceptance Criteria

- Each sub-task above is independently verifiable
- All interactive elements have appropriate hover/focus states
- Smart defaults reduce clicks for common workflows

---

## Reference: New and Modified API Endpoints

### New Endpoints

| Endpoint                                   | Method | Purpose                                         | Task |
| ------------------------------------------ | ------ | ----------------------------------------------- | ---- |
| `/api/provider-invoices/bulk-upload`       | POST   | Upload multiple PDFs, extract metadata          | 2    |
| `/api/provider-invoices/bulk-confirm`      | POST   | Confirm and create records from bulk upload     | 2    |
| `/api/reconciliation/{year}/{month}`       | GET    | Monthly reconciliation summary with match stats | 5    |
| `/api/bank-transactions/{id}/match`        | POST   | Confirm or reject a suggested match             | 3    |
| `/api/bank-transactions/{id}/manual-match` | POST   | Manually link a transaction to an invoice       | 3    |

### Modified Endpoints

| Endpoint                                   | Change                                                   | Task |
| ------------------------------------------ | -------------------------------------------------------- | ---- |
| `POST /api/bank-transactions/import`       | Add auto-matching logic after import                     | 3    |
| `POST /api/provider-invoices`              | Add auto-matching against existing transactions          | 3    |
| `GET /api/provider-invoices/{id}/download` | Must actually return the file (fix file path resolution) | 1    |

### MCP Tools to Add

| Tool                            | Purpose                                         | Task |
| ------------------------------- | ----------------------------------------------- | ---- |
| `create_provider_invoice`       | Create a single provider invoice record via AI  | 2c   |
| `create_provider_invoices_bulk` | Create multiple provider invoice records via AI | 2c   |
| `get_unmatched_transactions`    | Query unmatched bank transactions               | 3    |
| `get_unmatched_invoices`        | Query invoices without payment                  | 3    |
| `match_transaction_to_invoice`  | Link a transaction to an invoice                | 3    |

---

## Database Migration

Run these migrations before deploying Sprint 2 changes:

```sql
-- Add match tracking to bank_transactions
ALTER TABLE bank_transactions ADD COLUMN match_status TEXT DEFAULT 'unmatched';
ALTER TABLE bank_transactions ADD COLUMN match_confidence REAL;

-- Add payment tracking to provider_invoices
ALTER TABLE provider_invoices ADD COLUMN payment_status TEXT DEFAULT 'unpaid';
ALTER TABLE provider_invoices ADD COLUMN matched_transaction_id INTEGER REFERENCES bank_transactions(id);
ALTER TABLE provider_invoices ADD COLUMN amount_eur REAL;
ALTER TABLE provider_invoices ADD COLUMN bank_fee REAL;
ALTER TABLE provider_invoices ADD COLUMN fx_rate REAL;
```

**Note:** Check if `fx_rate` and `bank_fee` already exist on `bank_transactions` (they're in the blueprint). If so, also add them to `provider_invoices` for denormalized access. The `bank_transactions` columns store the raw values; the `provider_invoices` columns store the confirmed values after matching.

**Backfill:** For existing records, set `payment_status = 'matched'` where `matched_transaction_id IS NOT NULL` (or where a link already exists via a join). Set `amount_eur = amount` for EUR invoices.

---

## Python Dependencies to Add

```
pdfplumber>=0.10.0    # PDF text extraction for bulk upload
```

Alternative: `PyPDF2` or `pdfminer.six` if `pdfplumber` has issues. The key requirement is extracting structured text from the provider invoice PDFs.

---

## Testing Checklist

After completing all tasks, verify:

- [ ] Download works for all three provider categories (Junior FM, Cloud Engineer, Aeologic)
- [ ] Preview modal shows actual PDF content (not blank)
- [ ] Bulk PDF upload extracts metadata from known provider formats
- [ ] Review table after upload allows editing before confirmation
- [ ] MCP tools create provider invoice records successfully
- [ ] Bank import auto-matches transactions to invoices by invoice number
- [ ] Creating an invoice auto-matches to existing unlinked transactions
- [ ] Abstimmung page shows unmatched items from both directions
- [ ] Confirming a match calculates FX rate and records the bank debit as `amount_eur`
- [ ] Invoice generation uses `amount_eur` for foreign currency line items
- [ ] Distributed costs use bank payment amount as distribution base
- [ ] Kategorie-Detail shows cost breakdown for foreign currency categories
- [ ] Bank description tooltips show full text on hover
- [ ] Dashboard defaults to most recent month with data
- [ ] Invoice date defaults to end of selected month
- [ ] Category rows have hover effect
- [ ] Line items are filterable by client in Einstellungen
