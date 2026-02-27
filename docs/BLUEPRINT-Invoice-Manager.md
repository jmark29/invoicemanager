# Invoice Manager – Product Requirements Blueprint

> **Purpose:** Complete specification for a local web application that manages monthly invoicing for a consulting company. Designed to be handed to an AI coding agent for implementation.
> 
> **Date:** 2026-02-25
> **Author:** 29ventures GmbH

---

## 1. Problem Statement

29ventures GmbH bills its client DRS Holding AG a monthly invoice covering team services. The invoice contains 6 line items – 2 fixed-rate and 4 variable. The variable positions are sourced from different external providers, each with different billing cycles, currencies, and formats. Today, assembling these invoices is a tedious manual process involving Upwork CSV exports, provider invoices in EUR and USD, quarterly invoices that need to be distributed across months, and FX conversion with bank fees.

The goal is a local web application with a relational database that:

1. Stores all provider invoices, bank transactions, and Upwork data in structured form
2. Generates professional invoices (output format at implementor's discretion – DOCX from template, HTML-to-PDF, or other)
3. Tracks which costs have been billed to the client and which payments have been received
4. Enables flexible cost categories with keyword-based auto-matching against bank statements
5. Exposes an MCP (Model Context Protocol) server so that AI assistants (e.g., Claude Cowork) can query data, trigger invoice generation, and produce reports via natural language

---

## 2. Architecture Overview

```
┌──────────────────────────────────────────────────────┐
│                    Web Frontend                       │
│         (Dashboard, Data Entry, Reports)              │
└────────────────────┬─────────────────────────────────┘
                     │ REST API
┌────────────────────▼─────────────────────────────────┐
│                   Backend                             │
│   ┌─────────┐  ┌──────────┐  ┌────────────────────┐  │
│   │ Invoice │  │  Data    │  │ Invoice Renderer   │  │
│   │ Engine  │  │  Import  │  │                    │  │
│   └─────────┘  └──────────┘  └────────────────────┘  │
└────────────────────┬─────────────────────────────────┘
                     │
┌────────────────────▼─────────────────┐  ┌────────────┐
│     Relational Database (e.g.        │  │ MCP Server │
│     SQLite or similar)               │  │  Endpoint  │
│     (categories, invoices, costs,    │  └────────────┘
│      payments, upwork_txns, ...)     │
└──────────────────────────────────────┘
```

### Technology Stack (Recommendation – implementor may choose alternatives)

The following is a suggested stack. The implementor should choose whatever best fits their expertise and the requirements below. The critical constraints are: local-only operation, relational database, MCP server capability, and professional invoice output.

- **Backend:** Python (FastAPI) or Node.js or similar – implementor's choice
- **Database:** SQLite recommended (single-file, no installation needed), but any relational DB is fine
- **Frontend:** Implementor's choice – could be vanilla HTML/JS, React, Vue, HTMX, etc.
- **Invoice Output:** Multiple approaches are acceptable (see section 5):
  - Option A: Template-based DOCX editing (clone existing DOCX, modify XML)
  - Option B: HTML rendering → PDF conversion (e.g. via puppeteer, weasyprint, or similar)
  - Option C: Direct PDF generation
  - The key requirement is that the output matches the visual layout of the existing invoices (see reference template)
- **MCP Server:** Any MCP-compatible implementation for Claude integration

---

## 3. Data Model

### 3.1 `clients`

The entity being billed.

| Column        | Type    | Description                                   |
| ------------- | ------- | --------------------------------------------- |
| id            | TEXT PK | Short identifier, e.g. `"drs"`                |
| client_number | TEXT    | Number used in invoice numbering, e.g. `"02"` |
| name          | TEXT    | Full legal name: `"DRS Holding AG"`           |
| address_line1 | TEXT    | Street                                        |
| address_line2 | TEXT    | Optional second line                          |
| zip_city      | TEXT    | e.g. `"20457 Hamburg"`                        |
| vat_rate      | REAL    | e.g. `0.19`                                   |
| active        | BOOLEAN | Soft-delete flag                              |

### 3.2 `cost_categories`

Flexible, user-defined categories that group external costs. Each category represents a type of external service (e.g., "Cloud Engineer", "Junior FM Developer", "Mobile QA"). Categories are the central organizing concept – provider invoices, bank transactions, and invoice line items all reference categories.

| Column              | Type    | Description                                                                                                                                                      |
| ------------------- | ------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| id                  | TEXT PK | Slug identifier, e.g. `"cloud_engineer"`, `"junior_fm"`, `"aeologic_qa"`                                                                                         |
| name                | TEXT    | Display name, e.g. `"Cloud Engineer"`, `"Junior FileMaker Entwickler"`                                                                                           |
| provider_name       | TEXT    | Legal name of the provider, e.g. `"The Kaletsch Company Pty Ltd"`                                                                                                |
| provider_location   | TEXT    | e.g. `"Gillitts, South Africa"`                                                                                                                                  |
| currency            | TEXT    | `"EUR"` or `"USD"`                                                                                                                                               |
| hourly_rate         | REAL    | Current rate, nullable (Upwork: variable)                                                                                                                        |
| rate_currency       | TEXT    | Currency of the rate                                                                                                                                             |
| billing_cycle       | TEXT    | `"monthly"`, `"quarterly"`, `"weekly"` (Upwork), `"irregular"`                                                                                                   |
| cost_type           | TEXT    | How this cost is processed: `"direct"` (1:1 pass-through), `"distributed"` (spread across months), `"upwork"` (from Upwork export), `"fixed"` (constant monthly) |
| distribution_method | TEXT    | For `"distributed"`: `"working_days"` or `"equal"`                                                                                                               |
| vat_status          | TEXT    | `"standard"`, `"exempt"`, `"reverse_charge"`                                                                                                                     |
| bank_keywords       | TEXT    | JSON array of keywords for auto-matching bank transactions, e.g. `["KALETSCH", "RORY KALETSCH", "STOCKVILLE"]`                                                   |
| notes               | TEXT    | Free text                                                                                                                                                        |
| active              | BOOLEAN | Soft-delete flag                                                                                                                                                 |
| sort_order          | INTEGER | Display order in UI                                                                                                                                              |

**bank_keywords explained:** When importing bank statements, the system searches the Buchungstext (transaction description) for these keywords to automatically assign the transaction to the correct category. Multiple keywords increase matching accuracy. Keywords are matched case-insensitively.

### 3.3 `line_item_definitions`

Defines the structure of a client's invoice – which positions exist and how they are sourced. Each line item can optionally link to a `cost_category` to auto-populate its amount.

| Column       | Type       | Description                                                       |
| ------------ | ---------- | ----------------------------------------------------------------- |
| id           | INTEGER PK | Auto-increment                                                    |
| client_id    | TEXT FK    | → clients                                                         |
| position     | INTEGER    | Display position on invoice (1, 2, 3, ...)                        |
| label        | TEXT       | Description text on the invoice                                   |
| source_type  | TEXT       | `"fixed"`, `"category"`, `"manual"`                               |
| category_id  | TEXT FK    | → cost_categories (nullable for fixed/manual)                     |
| fixed_amount | REAL       | For `"fixed"` type only                                           |
| is_optional  | BOOLEAN    | If true, only included when there's a cost (e.g. travel expenses) |
| sort_order   | INTEGER    | Display order                                                     |

**Current DRS configuration (seed data):**

| Pos | Label                                                           | Type     | Category          | Amount      |
| --- | --------------------------------------------------------------- | -------- | ----------------- | ----------- |
| 1   | Team- & Projektmanagement und Konzeption                        | fixed    | –                 | 16,450.00 € |
| 2   | Senior FileMaker Entwickler                                     | fixed    | –                 | 8,300.00 €  |
| 3   | Junior FileMaker Entwickler                                     | category | junior_fm         | variable    |
| 4   | Serveradministration und AWS-Services                           | category | cloud_engineer    | variable    |
| 5   | Mobile Softwareentwickler                                       | category | upwork_mobile_dev | variable    |
| 6   | 2. Mobile Softwareentwickler, QA- und Business Analyst Services | category | aeologic_qa       | variable    |
| –   | Reisekosten                                                     | manual   | –                 | optional    |

**Seed data for cost_categories:**

| ID                  | Name                        | Provider                        | Currency | Cycle     | Cost Type   | Bank Keywords                                 |
| ------------------- | --------------------------- | ------------------------------- | -------- | --------- | ----------- | --------------------------------------------- |
| `junior_fm`         | Junior FileMaker Entwickler | Mikhail Iakovlev                | EUR      | monthly   | direct      | `["IAKOVLEV", "MIKHAIL"]`                     |
| `cloud_engineer`    | Cloud Engineer              | The Kaletsch Company Pty Ltd    | EUR      | quarterly | distributed | `["KALETSCH", "RORY KALETSCH", "STOCKVILLE"]` |
| `upwork_mobile_dev` | Mobile Softwareentwickler   | (via Upwork)                    | EUR      | weekly    | upwork      | `["UPWORK"]`                                  |
| `aeologic_qa`       | Mobile Dev, QA & BA         | Aeologic Technologies Pvt. Ltd. | USD      | irregular | direct      | `["AEOLOGIC", "AEOLOGIC TECHNOLOGIE"]`        |

### 3.4 `provider_invoices`

Incoming invoices from external providers. Each invoice belongs to a cost category. Users can upload the original invoice document (PDF) and the system stores it alongside the metadata.

| Column         | Type       | Description                                                                        |
| -------------- | ---------- | ---------------------------------------------------------------------------------- |
| id             | INTEGER PK | Auto-increment                                                                     |
| category_id    | TEXT FK    | → cost_categories                                                                  |
| invoice_number | TEXT       | Provider's invoice number, e.g. `"INV307"`, `"AEO000749"`, `"01/2025"`             |
| invoice_date   | DATE       | Date on the invoice                                                                |
| period_start   | DATE       | Service period start (nullable)                                                    |
| period_end     | DATE       | Service period end (nullable)                                                      |
| covers_months  | TEXT       | JSON array of months covered, e.g. `["2025-01","2025-02","2025-03"]` for quarterly |
| hours          | REAL       | Hours billed (nullable)                                                            |
| hourly_rate    | REAL       | Rate on this specific invoice                                                      |
| rate_currency  | TEXT       | `"EUR"` or `"USD"`                                                                 |
| amount         | REAL       | Invoice total in original currency                                                 |
| currency       | TEXT       | `"EUR"` or `"USD"`                                                                 |
| file_path      | TEXT       | Relative path to stored PDF, e.g. `"categories/junior_fm/ER2501-19.pdf"`           |
| notes          | TEXT       | Free text                                                                          |
| created_at     | DATETIME   |                                                                                    |

### 3.5 `bank_transactions`

Actual bank debits for provider payments.

| Column              | Type       | Description                                                             |
| ------------------- | ---------- | ----------------------------------------------------------------------- |
| id                  | INTEGER PK | Auto-increment                                                          |
| booking_date        | DATE       | Buchungstag                                                             |
| value_date          | DATE       | Wertstellung                                                            |
| transaction_type    | TEXT       | e.g. `"Überweisung"`                                                    |
| description         | TEXT       | Full Buchungstext                                                       |
| amount_eur          | REAL       | Amount debited in EUR (negative = outgoing)                             |
| reference           | TEXT       | Extracted payment reference (invoice number)                            |
| account_iban        | TEXT       | Source account                                                          |
| category_id         | TEXT FK    | → cost_categories (nullable, auto-matched via bank_keywords or manual)  |
| provider_invoice_id | INTEGER FK | → provider_invoices (nullable, linked by user)                          |
| fx_rate             | REAL       | If foreign currency, the effective exchange rate                        |
| bank_fee            | REAL       | Transfer fee (difference between bank debit and invoice EUR equivalent) |
| notes               | TEXT       |                                                                         |

### 3.6 `upwork_transactions`

Transactions from Upwork XLSX export.

| Column              | Type        | Description                                                           |
| ------------------- | ----------- | --------------------------------------------------------------------- |
| id                  | INTEGER PK  | Auto-increment                                                        |
| tx_id               | TEXT UNIQUE | Upwork transaction ID                                                 |
| tx_date             | DATE        | Transaction date                                                      |
| tx_type             | TEXT        | e.g. `"Hourly"`                                                       |
| description         | TEXT        | e.g. `"Invoice for Jan 26-Feb 1, 2026"`                               |
| period_start        | DATE        | Parsed billing period start                                           |
| period_end          | DATE        | Parsed billing period end                                             |
| amount_eur          | REAL        | Amount in EUR                                                         |
| freelancer_name     | TEXT        |                                                                       |
| contract_ref        | TEXT        | Upwork contract reference                                             |
| assigned_month      | TEXT        | Month this was billed to client, e.g. `"2026-02"` (null = unassigned) |
| assigned_invoice_id | INTEGER FK  | → generated_invoices (null = unassigned)                              |

**Upwork month-assignment rule:** A transaction is assigned to the month containing its **period end date**. Example: "Invoice for Dec 29, 2025-Jan 4, 2026" → assigned to January 2026 (end date is Jan 4).

### 3.7 `generated_invoices`

Outgoing invoices generated for clients.

| Column                 | Type        | Description                                                     |
| ---------------------- | ----------- | --------------------------------------------------------------- |
| id                     | INTEGER PK  | Auto-increment                                                  |
| client_id              | TEXT FK     | → clients                                                       |
| invoice_number         | TEXT UNIQUE | e.g. `"202501-02"`                                              |
| invoice_number_display | TEXT        | Number shown on invoice (without AR prefix)                     |
| filename               | TEXT        | e.g. `"AR202501-02.pdf"`                                        |
| period_year            | INTEGER     |                                                                 |
| period_month           | INTEGER     |                                                                 |
| invoice_date           | DATE        | Manually entered by user (see section 5.5)                      |
| net_total              | REAL        |                                                                 |
| vat_amount             | REAL        |                                                                 |
| gross_total            | REAL        |                                                                 |
| status                 | TEXT        | `"draft"`, `"sent"`, `"paid"`, `"overdue"`                      |
| file_path              | TEXT        | Path to generated invoice file (DOCX, PDF, or HTML)             |
| pdf_path               | TEXT        | Path to PDF version (nullable if primary output is already PDF) |
| sent_date              | DATE        | When invoice was sent to client                                 |
| created_at             | DATETIME    |                                                                 |
| notes                  | TEXT        |                                                                 |

### 3.8 `generated_invoice_items`

Line items on each generated invoice – the core traceability link.

| Column                   | Type       | Description                                                             |
| ------------------------ | ---------- | ----------------------------------------------------------------------- |
| id                       | INTEGER PK | Auto-increment                                                          |
| invoice_id               | INTEGER FK | → generated_invoices                                                    |
| position                 | INTEGER    | Position number (1-6+)                                                  |
| label                    | TEXT       | Description text                                                        |
| amount                   | REAL       | EUR amount billed                                                       |
| source_type              | TEXT       | `"fixed"`, `"direct"`, `"distributed"`, `"upwork"`, `"manual"`          |
| category_id              | TEXT FK    | → cost_categories (nullable)                                            |
| provider_invoice_id      | INTEGER FK | → provider_invoices (nullable, for direct costs)                        |
| distribution_source_id   | INTEGER FK | → provider_invoices (for distributed costs: link to the source invoice) |
| distribution_months_json | TEXT       | For distributed: JSON with per-month breakdown                          |
| upwork_tx_ids_json       | TEXT       | For upwork: JSON array of upwork_transaction IDs                        |
| notes                    | TEXT       |                                                                         |

### 3.9 `payment_receipts`

Incoming payments from clients.

| Column             | Type       | Description                       |
| ------------------ | ---------- | --------------------------------- |
| id                 | INTEGER PK | Auto-increment                    |
| client_id          | TEXT FK    | → clients                         |
| payment_date       | DATE       |                                   |
| amount_eur         | REAL       |                                   |
| reference          | TEXT       | Bank reference / Verwendungszweck |
| matched_invoice_id | INTEGER FK | → generated_invoices (nullable)   |
| notes              | TEXT       |                                   |

### 3.10 `working_days_config`

Configuration for working-day calculations.

| Column      | Type       | Description     |
| ----------- | ---------- | --------------- |
| id          | INTEGER PK |                 |
| country     | TEXT       | `"DE"`          |
| state       | TEXT       | `"HE"` (Hessen) |
| description | TEXT       |                 |

Working days = Monday through Friday, excluding public holidays for the configured state. The public holiday calculation must include Easter-dependent holidays (Karfreitag, Ostermontag, Christi Himmelfahrt, Pfingstmontag, Fronleichnam) using the Anonymous Gregorian Easter algorithm.

**Hessen public holidays:**

- Neujahr (Jan 1)
- Karfreitag (Easter - 2 days)
- Ostermontag (Easter + 1 day)
- Tag der Arbeit (May 1)
- Christi Himmelfahrt (Easter + 39 days)
- Pfingstmontag (Easter + 50 days)
- Fronleichnam (Easter + 60 days) – Hessen-specific!
- Tag der Deutschen Einheit (Oct 3)
- 1. Weihnachtstag (Dec 25)
- 2. Weihnachtstag (Dec 26)

---

## 4. Business Rules

### 4.1 Invoice Numbering

- **Format:** `{YYYY}{MM}-{client_number}` → e.g. `202501-02`
- **Filename prefix:** `AR` → filename is `AR202501-02.docx`
- The `AR` prefix appears ONLY in the filename, NOT in the invoice text
- Sequential per client and month; one invoice per client per month

### 4.2 Fixed Line Items

Positions 1 and 2 have fixed monthly amounts. These are stored in `line_item_definitions` and do not change month to month (unless the definition is updated).

### 4.3 Cost Type: "direct" (Example: Junior FM – Pos 3)

For categories with `cost_type = "direct"`:

- One or more provider invoices per month → the amount billed to the client equals the invoice total (or, for foreign currency, the EUR bank debit amount)
- If the category's currency is EUR: amount = provider invoice total
- If the category's currency is USD (or other foreign currency): amount = EUR bank debit amount (including FX conversion and bank fees). The provider invoice must be linked to a bank transaction to determine this.
- Multiple invoices may be combined in one month's billing

**Current example (Junior FM / `junior_fm`):**
Monthly invoices, EUR only, no VAT (Austrian Kleinunternehmerregelung), €50/h

**Current example (Aeologic / `aeologic_qa`):**
Irregular invoices in USD, paid via international bank transfer with ~€22.50 FX/transfer fee. Rate changed from $25/h to $28/h in May 2025. The amount passed through to the client is the actual EUR bank debit.

### 4.4 Cost Type: "distributed" (Example: Cloud Engineer – Pos 4)

For categories with `cost_type = "distributed"`:

- A single invoice covers multiple months (e.g., quarterly)
- The `covers_months` field on the provider_invoice specifies which months are covered
- The total amount must be **distributed across those months by working days**
- **Distribution base:** The total amount to distribute is the **bank payment amount** (invoice + bank fee), as bank fees are passed through to the client
- **Formula:** For months M1, M2, ... Mn with working days W1, W2, ... Wn:
  - `amount_Mi = total × Wi / sum(W)`, rounded to 2 decimal places
  - Last month gets the remainder (`total - sum(other months)`) to avoid rounding drift
- Working days are calculated per section 3.10 (Hessen holidays)
- The `generated_invoice_items` record stores which source invoice was used and the distribution breakdown

**Current example (Kaletsch / `cloud_engineer`):**
Quarterly invoices at €36/h, paid via international transfer with ~€15 bank fee.

### 4.5 Cost Type: "upwork" (Example: Mobile Dev – Pos 5)

For categories with `cost_type = "upwork"`:

- Data sourced from Upwork XLSX export, not from manual invoice upload
- Weekly billing periods that can span month boundaries
- **Assignment rule:** Transaction assigned to the month of the period **end date**
- Example: "Invoice for Dec 29, 2025 - Jan 4, 2026" → January 2026
- Transactions must be tracked to prevent double-counting
- Source: XLSX export from Upwork with columns: Date, Transaction ID, Type, Summary/Description, Reference ID, Amount, Currency
- **Parsing:** Extract period start/end from the "Summary" field using regex. Formats to handle:
  - `"Invoice for Feb 16-Feb 22, 2026"` (same month)
  - `"Invoice for Dec 29, 2025-Jan 4, 2026"` (cross-month, cross-year)
- Monthly total = sum of all transactions assigned to that month

### 4.6 Cost Type: "fixed"

For line items with `source_type = "fixed"`:

- The amount is constant and stored in `line_item_definitions.fixed_amount`
- No external data source needed

### 4.7 Optional Line Items

- Travel expenses ("Reisekosten") are added only when applicable
- These are entered manually with a label and amount
- They appear as additional positions on the invoice (after Pos 6)

### 4.8 VAT Calculation

- VAT rate: 19% (configurable per client)
- Net total = sum of all line items
- VAT = net_total × 0.19, rounded to 2 decimal places (ROUND_HALF_UP)
- Gross total = net + VAT
- All amounts on the invoice are in EUR, formatted as German locale: `1.234,56 €`

### 4.9 German Number Formatting

All monetary amounts on the invoice use German formatting:

- Thousand separator: `.` (period)
- Decimal separator: `,` (comma)
- Currency suffix: ` €`
- Example: `16.450,00 €`, `42.287,60 €`

---

## 5. Invoice Output Generation

### 5.1 Output Format (Implementor's Choice)

The invoice output must be a professional, printable document that visually matches the existing invoice layout. The implementor may choose the rendering approach:

**Option A: Template-based DOCX editing**

- Clone an existing DOCX invoice, modify XML content, produce DOCX + PDF
- Advantage: Pixel-perfect match to existing layout
- A reference template (`AR202506-02.docx`) is provided in the project folder

**Option B: HTML rendering to PDF**

- Render an HTML page with CSS matching the invoice layout, convert to PDF
- Advantage: Easier to maintain, no XML manipulation needed
- The HTML can also serve as a preview in the web UI before finalizing

**Option C: Direct PDF generation**

- Generate PDF directly using a library
- Advantage: Single output format, no intermediate step

Regardless of approach, the output must include all elements described in section 5.2.

### 5.2 Invoice Content Structure

Every generated invoice must contain these elements:

**Header area:**

- Company logo and contact information (29ventures GmbH, Wiesbaden)
- Client address block (name, street, zip/city)
- Invoice number (e.g. `Rechnung 202501-02`)
- Service period (e.g. `Leistungszeitraum 01.01.2025 bis 31.01.2025`)
- Invoice date and location (e.g. `Wiesbaden, 28.02.2025`)

**Line items table with columns:**

- Position number (1, 2, 3, ...)
- Description (label text)
- Amount in EUR (German-formatted)

**Summary section:**

- Netto-Rechnungsbetrag (net total)
- Umsatzsteuer 19% (VAT)
- Brutto-Rechnungsbetrag (gross total)

**Footer:**

- Bank details, company registration info

### 5.3 Reference Layout Details

For implementors who want to match the existing layout precisely:

- Page size: A4
- Font: Helvetica Neue Light
- Table columns: Position (narrow), Description (wide, ~75% of table width), Amount (right-aligned)
- Summary rows span the full table width
- German number formatting throughout (see section 4.9)

A reference DOCX template (`AR202506-02.docx`) is included in the project folder. If using DOCX template editing, be aware that text in DOCX XML is often split across multiple `<w:r>` (run) elements and the replacement logic must handle this correctly.

### 5.4 Generation Workflow

1. User selects client and month in the UI
2. System auto-populates amounts from database (see section 6.2)
3. User reviews and can override any amount
4. **User manually enters or confirms the invoice number and invoice date** (two input fields – see section 5.5)
5. User triggers generation
6. System renders the invoice in the chosen format
7. System stores the record in `generated_invoices` + `generated_invoice_items`
8. Output file (DOCX, PDF, or both) is stored and made available for download

### 5.5 Invoice Number and Date (Manual Entry)

The invoice number and invoice date are **user-entered fields** in the generation form, not auto-generated:

- **Invoice number:** Pre-filled with a suggestion based on the numbering format (`{YYYY}{MM}-{client_number}`), but editable. The user must confirm or modify before generating.
- **Invoice date:** Defaults to today's date, but the user can set any date. Displayed as `DD.MM.YYYY` on the invoice.

This allows flexibility for backdating, corrections, or custom numbering schemes. A future enhancement could add auto-increment logic, but for v1, manual entry with a smart default is sufficient.

---

## 6. Functional Requirements

### 6.1 Data Import

#### FR-IMP-01: Upload Provider Invoices

- User selects a **cost category** first, then uploads invoice documents (PDFs)
- The upload UI is category-aware: user picks the category (e.g., "Cloud Engineer"), then uploads one or more invoice files
- Auto-extract metadata where possible (date, amount, invoice number from filename patterns)
- Manual entry/correction of all fields (invoice number, date, amount, hours, period)
- Store PDF file in organized directory structure: `data/categories/{category_id}/{filename}`

#### FR-IMP-02: Upload Upwork Transactions

- Accept Upwork XLSX export
- Parse all rows, extract period start/end dates from Summary field
- Detect and skip already-imported transactions (by tx_id)
- Auto-assign to months based on period end date
- Show preview before committing import

#### FR-IMP-03: Upload Bank Statements

- Accept bank statement XLSX (format: Buchungstag, Wertstellung, Umsatzart, Buchungstext, Betrag, RK, Buchungsjahr)
- Parse payment references from Buchungstext to extract invoice numbers
- **Auto-match to cost categories** by searching the Buchungstext for the category's `bank_keywords` (case-insensitive substring match)
- Auto-link to provider invoices by matching invoice number in the Buchungstext reference
- Highlight unmatched transactions for manual assignment
- Calculate bank fees (difference between bank debit and invoice amount)
- Calculate effective FX rate for foreign currency payments

#### FR-IMP-04: Upload Payment Receipts (Incoming)

- Record incoming payments from clients
- Match to generated invoices by reference number
- Update invoice status to "paid" when fully matched

### 6.2 Invoice Generation

#### FR-GEN-01: Generate Monthly Invoice

- Select client and month
- **Two manual input fields at the top:** invoice number (pre-filled with suggestion) and invoice date (defaults to today)
- System automatically determines amounts for each position based on the linked cost category:
  - `fixed` positions: from `line_item_definitions`
  - `category` positions with `direct` cost type: lookup from `provider_invoices` + `bank_transactions` for the month
  - `category` positions with `distributed` cost type: find the multi-month invoice covering this month, distribute by working days
  - `category` positions with `upwork` cost type: sum all `upwork_transactions` assigned to this month
- Show preview with all amounts before generating
- Allow manual override of any amount (with free-text reason field)
- Generate invoice output (format per section 5)
- Record in `generated_invoices` + `generated_invoice_items` with full traceability

#### FR-GEN-02: Dry-Run Mode

- Calculate and display all amounts without generating files or updating the database
- Highlight missing data (e.g., no provider invoice for a month, no bank payment linked)

#### FR-GEN-03: PDF Output

- Ensure a PDF version of every invoice is available (either generated directly or converted from DOCX/HTML)
- Store PDF for download and archival

#### FR-GEN-04: Re-generate Invoice

- Allow re-generating an invoice with corrected data
- Keep audit trail of previous versions

### 6.3 Dashboard & Reporting

#### FR-DASH-01: Monthly Overview

- For each month, show:
  - Status of each provider invoice (received? linked to bank payment?)
  - Upwork transaction count and total for the month
  - Generated invoice status (draft/sent/paid)
  - Outstanding amount

#### FR-DASH-02: Category Cost Summary

- Per-category breakdown: invoiced amount, bank payment, fees, open items
- Time-series view of monthly costs per category
- Drill-down into individual invoices and bank transactions per category

#### FR-DASH-03: Accounts Receivable

- List of all generated invoices with status
- Days outstanding calculation
- Payment matching status
- Overdue alerts

#### FR-DASH-04: Reconciliation View

- Side-by-side comparison:
  - Provider invoices ↔ Bank payments (are all invoices paid?)
  - Generated invoices ↔ Client payments (has the client paid?)
- Highlight discrepancies

### 6.4 Data Management

#### FR-DATA-01: Cost Category Management (CRUD)

- Add, edit, deactivate cost categories
- Configure bank_keywords for auto-matching (add/remove keywords per category)
- Track rate changes over time (rate history per category)
- View all invoices and bank transactions linked to a category

#### FR-DATA-02: Client Management (CRUD)

- Add, edit clients
- Configure line item structure per client (which categories map to which invoice positions)

#### FR-DATA-03: Manual Adjustments

- Override any auto-calculated amount with manual entry + reason
- Add ad-hoc line items (travel expenses, etc.)

---

## 7. MCP Server Integration

### 7.1 Purpose

The application exposes an MCP (Model Context Protocol) server that allows AI assistants like Claude (via Cowork mode) to interact with the invoice system programmatically. This enables natural-language workflows like:

- *"Generate the invoice for February 2026"*
- *"What's the total billed to DRS in Q4 2025?"*
- *"Are there any unpaid invoices?"*
- *"Show me the Aeologic costs for the last 6 months"*
- *"Which provider invoices are missing for January?"*

### 7.2 MCP Tools to Expose

#### Query Tools (Read-Only)

| Tool                  | Description                                   | Parameters                        |
| --------------------- | --------------------------------------------- | --------------------------------- |
| `get_invoice_status`  | Get status of a specific invoice              | month, client_id                  |
| `get_month_overview`  | Get all cost data for a month                 | month                             |
| `get_open_invoices`   | List unpaid client invoices                   | client_id (optional)              |
| `get_category_costs`  | Get costs for a category over time            | category_id, from_month, to_month |
| `get_reconciliation`  | Show payment matching status                  | month or category_id              |
| `get_missing_data`    | List what's missing for a month               | month                             |
| `get_upwork_summary`  | Upwork transactions for a month               | month                             |
| `search_transactions` | Search across all transaction types           | query string                      |
| `get_working_days`    | Calculate working days for a month            | year, month                       |
| `get_distribution`    | Calculate distribution for a quarterly amount | total, months[]                   |

#### Action Tools (Write)

| Tool                      | Description                                   | Parameters                             |
| ------------------------- | --------------------------------------------- | -------------------------------------- |
| `generate_invoice`        | Generate a monthly invoice                    | month, client_id, overrides (optional) |
| `import_upwork_xlsx`      | Import Upwork transactions from file          | file_path                              |
| `import_bank_statement`   | Import bank statement from file               | file_path                              |
| `record_provider_invoice` | Add a provider invoice record                 | category_id, invoice_data              |
| `link_bank_payment`       | Link a bank transaction to a provider invoice | bank_tx_id, provider_invoice_id        |
| `record_payment`          | Record an incoming client payment             | client_id, amount, date, reference     |
| `update_invoice_status`   | Change invoice status                         | invoice_id, new_status                 |

### 7.3 MCP Resources

| Resource                            | Description                                            |
| ----------------------------------- | ------------------------------------------------------ |
| `invoices://overview/{month}`       | Monthly data overview                                  |
| `invoices://client/{client_id}`     | Client configuration and history                       |
| `invoices://category/{category_id}` | Cost category details, invoices, and bank transactions |

---

## 8. Seed Data

The system should be initialized with historical data from January–June 2025. This data validates that the system produces the same results as the manually-created invoices.

### 8.1 Historical Invoices (Validation Baseline)

| Invoice   | Month  | Pos 1     | Pos 2    | Pos 3    | Pos 4    | Pos 5    | Pos 6    | Net        | VAT      | Gross     |
| --------- | ------ | --------- | -------- | -------- | -------- | -------- | -------- | ---------- | -------- | --------- |
| 202501-02 | Jan 25 | 16,450.00 | 8,300.00 | 1,300.00 | 2,851.20 | 5,083.19 | 1,551.41 | 35,535.80  | 6,751.80 | 42,287.60 |
| 202502-02 | Feb 25 | 16,450.00 | 8,300.00 | 3,800.00 | 2,592.00 | 4,200.84 | 1,036.28 | 36,666.09* | 6,966.56 | 43,632.65 |
| 202503-02 | Mar 25 | 16,450.00 | 8,300.00 | 2,000.00 | 2,851.80 | 3,843.43 | 5,079.51 | 38,524.74  | 7,319.70 | 45,844.44 |
| 202504-02 | Apr 25 | 16,450.00 | 8,300.00 | 2,000.00 | 2,851.20 | 3,884.03 | 8,238.89 | 41,724.12  | 7,927.58 | 49,651.70 |
| 202505-02 | May 25 | 16,450.00 | 8,300.00 | 1,600.00 | 2,851.20 | 4,145.25 | 6,122.20 | 39,468.65  | 7,499.04 | 46,967.69 |
| 202506-02 | Jun 25 | 16,450.00 | 8,300.00 | 1,800.00 | 2,851.20 | 4,673.70 | 2,512.79 | 36,587.69  | 6,951.66 | 43,539.35 |

*Feb 2025 includes additional Reisekosten: 286.97 €*

### 8.2 Junior FM Invoices (Pos 3 Source)

| Month   | Invoice Nr | Hours | Rate   | Amount  |
| ------- | ---------- | ----- | ------ | ------- |
| 2025-01 | 01/2025    | 26    | 50 €/h | 1,300 € |
| 2025-02 | 02/2025    | 76    | 50 €/h | 3,800 € |
| 2025-03 | 03/2025    | 40    | 50 €/h | 2,000 € |
| 2025-04 | 04/2025    | 40    | 50 €/h | 2,000 € |
| 2025-05 | 05/2025    | 32    | 50 €/h | 1,600 € |
| 2025-06 | 06/2025    | 36    | 50 €/h | 1,800 € |
| 2025-07 | 07/2025    | 32    | 50 €/h | 1,600 € |
| 2025-08 | 08/2025    | 14    | 50 €/h | 700 €   |
| 2025-09 | 09/2025    | 32    | 50 €/h | 1,600 € |
| 2025-10 | 10/2025    | 32    | 50 €/h | 1,600 € |
| 2025-11 | 11/2025    | 32    | 50 €/h | 1,600 € |
| 2025-12 | 12/2025    | 32    | 50 €/h | 1,600 € |

### 8.3 Kaletsch / Cloud Engineer Invoices (Pos 4 Source)

| Invoice | Quarter | Hours | Rate   | Amount     | Bank Payment | Bank Fee |
| ------- | ------- | ----- | ------ | ---------- | ------------ | -------- |
| INV307  | Q1 2025 | 230   | 36 €/h | 8,280.00 € | 8,295.00 €   | 15.00 €  |
| INV308  | Q2 2025 | 234   | 36 €/h | 8,424.00 € | 8,439.14 €   | 15.14 €  |
| INV314  | Q3 2025 | 260.3 | 36 €/h | 9,370.80 € | 9,387.36 €   | 16.56 €  |
| INV320  | Q4 2025 | 237.6 | 36 €/h | 8,553.60 € | 8,568.93 €   | 15.33 €  |

Note: INV314 (Q3) includes a 22.7h adjustment for Q2.

### 8.4 Aeologic Invoices (Pos 6 Source)

| Invoice   | Date       | USD Amount | Hours | Rate  | Bank EUR  | Bank Date  |
| --------- | ---------- | ---------- | ----- | ----- | --------- | ---------- |
| AEO000716 | 2024-12    | $900       | –     | $25/h | €899.89   | 2025-01-06 |
| AEO000729 | 2025-01-30 | $1,650     | 66    | $25/h | €1,477.40 | 2025-05-26 |
| AEO000741 | 2025-02-28 | $1,100     | 44    | $25/h | €1,036.28 | 2025-03-31 |
| AEO000749 | 2025-03-25 | $5,500     | 220   | $25/h | €5,079.51 | 2025-04-07 |
| AEO000768 | 2025-05-01 | $9,075     | 363   | $25/h | €8,092.64 | 2025-05-23 |
| AEO000777 | 2025-05-30 | $7,140     | 255   | $28/h | €6,122.20 | 2025-07-07 |
| AEO000789 | 2025-07-01 | $2,898     | 103.5 | $28/h | €2,512.79 | 2025-08-14 |
| AEO000811 | 2025-08-29 | $1,456     | 52    | $28/h | €1,276.43 | 2025-09-26 |
| AEO000819 | 2025-09-30 | $784       | 28    | $28/h | –         | –          |
| AEO000828 | 2025-10-31 | $1,246     | 44.5  | $28/h | –         | –          |
| AEO000844 | 2025-12-01 | $812       | 29    | $28/h | –         | –          |
| AEO000852 | 2025-12-30 | $1,302     | 46.5  | $28/h | –         | –          |
| AEO000861 | 2026-02-03 | $952       | 34    | $28/h | –         | –          |

---

## 9. Data Organization

The implementor should organize the project as they see fit. The key requirement for **stored files** is:

```
data/
├── database file              # Relational database (e.g., invoices.db for SQLite)
├── templates/                 # Invoice template(s) – reference DOCX included
│   └── AR202506-02.docx       # Reference template for layout matching
├── generated/                 # Generated invoices (DOCX/PDF/HTML), organized by year
│   ├── 2025/
│   └── 2026/
├── categories/                # Uploaded provider invoices, one folder per category
│   ├── junior_fm/
│   ├── cloud_engineer/
│   ├── aeologic_qa/
│   └── upwork_mobile_dev/
└── imports/                   # Uploaded source files (Upwork XLSX, bank statements)
```

The category-based folder structure ensures that uploaded documents are automatically organized by the cost category they belong to.

---

## 10. Non-Functional Requirements

### NFR-01: Local-Only Operation

The application runs entirely locally. No cloud services, no external API calls (except MCP connections from Claude). All data stays on the user's machine.

### NFR-02: Single-User

Designed for single-user operation. No authentication needed for the web UI. MCP access is also single-user.

### NFR-03: Data Integrity

- All monetary calculations use `Decimal` with `ROUND_HALF_UP` to 2 decimal places
- Foreign key constraints enforced
- Soft-delete for clients and cost categories (never lose data)

### NFR-04: Audit Trail

- Every generated invoice stores full traceability: which provider invoices, which bank transactions, which Upwork transactions were used
- Invoice re-generation preserves previous versions

### NFR-05: Portability

- SQLite = single file, easily backed up
- All file references are relative paths
- Works on macOS and Linux

### NFR-06: Extensibility

- Data model supports multiple clients
- New cost categories can be added via the UI without code changes
- New line item definitions can be configured per client, linking to any category
- Bank keyword matching is fully user-configurable per category
- MCP tools are modular and can be extended

---

## 11. Open Questions / Future Scope

These items are explicitly out of scope for v1 but should be considered in the data model:

1. **Multi-client support:** The data model already supports it, but the UI may focus on DRS initially
2. **Automated email sending:** Send invoices directly from the app
3. **Dunning / payment reminders:** Automated overdue notifications
4. **Currency rate history:** Store daily EUR/USD rates for retrospective analysis
5. **Dynamic table rows:** Adding/removing line items in the DOCX template (currently all 6 positions must exist in the template)
6. **Upwork API integration:** Direct API access instead of manual XLSX export
7. **OCR for invoice import:** Auto-extract data from scanned provider invoices

---

## 12. Acceptance Criteria

The system is considered complete when:

1. **All seed data loaded:** All historical invoices (Jan–Jun 2025), provider invoices, bank transactions, and cost categories are in the database
2. **Invoice generation works:** Generating an invoice for a historical month produces the correct amounts matching the reference data in section 8.1
3. **Invoice number and date editable:** The generation form allows manual entry of both fields with smart defaults
4. **Cost categories configurable:** Categories can be added, edited, and deactivated. Bank keywords can be configured per category
5. **Bank statement matching works:** Importing a bank statement XLSX auto-matches transactions to categories via keywords and to invoices via reference numbers
6. **Working days correct:** Working day calculation matches the reference values used in historical invoices
7. **Upwork import works:** Importing the Upwork XLSX correctly assigns transactions to months by period end date, with no double-counting
8. **MCP tools functional:** All MCP tools listed in section 7.2 respond correctly
9. **Dashboard shows:** Monthly overview, open items, reconciliation status for all months with data
