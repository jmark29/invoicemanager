# Invoice Manager — User Guide

## 1. How to Run the App

### Quick Start

Run all commands from the project root (`invoicemanager/`):

```bash
make setup   # one-time: installs Python + Node dependencies
make dev     # starts backend (:8000) + frontend (:5173)
```

Open http://localhost:5173 — that's it.

On first startup the backend automatically runs migrations, creates the database, and loads seed data (Jan–Jun 2025).

### Prerequisites

| Requirement     | Version | Install                                                                 |
| --------------- | ------- | ----------------------------------------------------------------------- |
| Python          | 3.11+   |                                                                         |
| uv              | latest  | `brew install uv` or `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Node.js         | 18+     | `brew install node`                                                     |
| WeasyPrint libs | —       | macOS: `brew install pango cairo libffi`                                |

For PDF generation on macOS, add this to your `~/.zshrc`:

```bash
export DYLD_LIBRARY_PATH=/opt/homebrew/lib
```

### Makefile Targets

| Command         | What it does                                   |
| --------------- | ---------------------------------------------- |
| `make setup`    | Install Python and Node dependencies           |
| `make dev`      | Start backend + frontend together              |
| `make backend`  | Start backend only                             |
| `make frontend` | Start frontend only                            |
| `make test`     | Run backend + frontend tests                   |
| `make seed`     | Manually re-seed database (usually not needed) |

### Other Useful URLs

| What             | URL                        |
| ---------------- | -------------------------- |
| App              | http://localhost:5173      |
| Swagger API docs | http://localhost:8000/docs |

### Starting Without Make

If you prefer running things manually:

```bash
# Terminal 1 — backend
uv run uvicorn backend.main:app --reload --port 8000

# Terminal 2 — frontend
cd frontend && npm run dev
```

---

## 2. Functionality Explained

### Navigation

The left sidebar contains all pages. Labels are in German to match the invoice terminology.

### Dashboard (Home)

The landing page. Shows a month/year selector at the top.

- **Yearly summary cards** — total invoices, net + gross totals, open (unpaid) invoices, status breakdown (draft/sent/paid/overdue)
- **Monthly invoice table** — invoices for the selected month with number, date, net, gross, status
- **Reconciliation summary** — matched provider invoices, unmatched bank transactions, payment status
- **Quick-action links** — shortcuts to Bank Import, Upwork Import, Provider Invoices, Payments, Reconciliation

### Rechnungen (Invoices)

Lists all generated invoices. You can:

- **Filter** by year, status, or client
- **Download** a PDF for any invoice
- **Change status** via the dropdown (draft → sent → paid / overdue)
- **Click** an invoice number to view its detail page

**Invoice Detail Page** shows all line items, totals (net / 19% VAT / gross), notes, linked payments, and actions:

- **Neu generieren** (Regenerate) — archives the old PDF and generates a fresh one using current data. Only available for draft or overdue invoices.
- **Download PDF**

### Rechnung erstellen (Generate Invoice)

A 4-step wizard:

1. **Select month & client** — pick the billing month and client, then click **Vorschau** (Preview)
2. **Review line items** — the system resolves each position's amount based on its cost type (see below). You can override any amount with a custom value. Warnings appear if source data is missing. Running totals are shown at the bottom.
3. **Invoice metadata** — set invoice number (format `YYYYMM-XX`), invoice date, and optional notes
4. **Done** — download the PDF, view the invoice, or generate another

### The 4 Cost Types

Every variable line item is resolved through one of these:

| Type            | How it works                                                                                                                                            | Example                      |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------- |
| **Fixed**       | Constant amount defined in Settings                                                                                                                     | Projektmanagement, Senior FM |
| **Direct**      | 1:1 pass-through of a provider invoice. EUR invoices use the invoice amount; USD invoices use the EUR bank debit (includes FX + fees)                   | Junior FM, Aeologic          |
| **Distributed** | A quarterly invoice distributed across 3 months by Hessen working days. Base amount = bank payment (invoice + bank fee). Last month gets the remainder. | Cloud Engineer (Kaletsch)    |
| **Upwork**      | Sum of Upwork transactions assigned to the month. Assignment rule: the period END date determines the month.                                            | Mobile Dev                   |

### Abstimmung (Reconciliation)

Monthly reconciliation view. Select a month to see:

- **Provider Invoices vs Bank Payments** — each provider invoice paired with its bank payment. Rows without a bank payment are highlighted in amber.
- **Unmatched Bank Transactions** — bank transactions not linked to any provider invoice
- **Invoice Payment Status** — gross total vs total paid, with outstanding balance highlighted

### Kategorien (Cost Categories)

View all cost categories (Junior FM, Cloud Engineer, Upwork, Aeologic). Click a category to see:

- Configuration (cost type, billing cycle, currency, VAT status, bank keywords)
- Linked provider invoices
- Linked bank transactions

### Lieferantenrechnungen (Provider Invoices)

List of all provider invoices. Filter by category or assigned month. Shows invoice number, category, date, amount, currency, and assigned month.

### Bank (Bank Transactions)

- **Import** — drag-and-drop a bank XLSX file. The system parses it, auto-matches transactions to categories using the `bank_keywords` on each cost category, and shows import stats (imported, duplicates skipped, auto-matched).
- **Review** — transactions without a category are highlighted in yellow. Assign a category manually via the dropdown.

### Upwork (Upwork Transactions)

- **Import** — optionally select a category first, then drag-and-drop the Upwork XLSX. The system parses transactions and auto-assigns months based on the period end date.
- **Month summary cards** — show the total EUR amount per month
- **Table** — date, transaction ID, description, amount, freelancer, assigned month

### Zahlungen (Payments)

Record invoice payments:

- **Create** — enter date, amount, reference, optionally link to an invoice, add notes
- **List** — view all payments with their linked invoices
- **Delete** — with confirmation dialog

### Einstellungen (Settings)

Two sections:

- **Client Settings** — edit name, client number, address, VAT rate. Click Speichern to save.
- **Line Item Settings** — table of invoice positions. Click a row to edit the label or fixed amount inline.

---

## 3. User Tests

Work through these after starting the app with seed data loaded.

### Validation Reference

These are the known-correct totals for Jan–Jun 2025. Use them to verify generated invoices.

| Month   | Net (EUR) | VAT 19%  | Gross (EUR) |
| ------- | --------- | -------- | ----------- |
| 2025-01 | 35.535,80 | 6.751,80 | 42.287,60   |
| 2025-02 | 36.666,09 | 6.966,56 | 43.632,65   |
| 2025-03 | 38.524,74 | 7.319,70 | 45.844,44   |
| 2025-04 | 41.724,12 | 7.927,58 | 49.651,70   |
| 2025-05 | 39.468,65 | 7.499,04 | 46.967,69   |
| 2025-06 | 36.587,69 | 6.951,66 | 43.539,35   |

*Note: Feb 2025 includes Reisekosten of 286,97 EUR.*

### Test Checklist

#### T1 — Startup & Seed Data

- [ ] `make setup` completes without errors
- [ ] `make dev` starts both backend (:8000) and frontend (:5173)
- [ ] Backend log shows "Seed data loaded on first startup" (first run only)
- [ ] Opening http://localhost:5173 shows the Dashboard with data

#### T2 — Dashboard

- [ ] Select January 2025 — summary cards show data
- [ ] Navigate to February 2025 using the arrow — data updates
- [ ] Quick-action links navigate to the correct pages

#### T3 — Generate January 2025 Invoice

- [ ] Go to "Rechnung erstellen"
- [ ] Select January 2025 and client DRS Holding AG, click Vorschau
- [ ] Preview shows 6–7 line items with resolved amounts
- [ ] Verify the net total matches 35.535,80 EUR
- [ ] Set invoice number to `202501-02`, set date, click generate
- [ ] PDF downloads successfully

#### T4 — Validate All 6 Months

- [ ] Generate invoices for Feb–Jun 2025 in the same way
- [ ] Compare each month's net, VAT, and gross against the validation table above
- [ ] All 6 invoices appear in the Rechnungen list

#### T5 — Bank Import

- [ ] Go to "Bank"
- [ ] Upload `docs/reference-docs/Kontoumsätze Aeologic + Kaletsch.xlsx`
- [ ] Import stats show number of transactions imported and auto-matched
- [ ] Verify some transactions are auto-matched to categories (green/assigned)
- [ ] Verify unmatched transactions are highlighted in yellow
- [ ] Manually assign a category to one yellow row — verify it saves

#### T6 — Upwork Import

- [ ] Go to "Upwork"
- [ ] Upload `docs/reference-docs/upwork-transactions_20260225.xlsx`
- [ ] Import stats show ~214 transactions imported
- [ ] Month summary cards appear with per-month totals
- [ ] Filter by a specific month — table filters correctly

#### T7 — Reconciliation

- [ ] Go to "Abstimmung"
- [ ] Select January 2025
- [ ] Verify matched provider invoices count
- [ ] Check for any unmatched bank transactions (amber rows)
- [ ] If an invoice was generated, verify the payment status section shows gross and balance

#### T8 — Payments

- [ ] Go to "Zahlungen"
- [ ] Create a payment: select DRS Holding AG, enter today's date, amount 42.287,60, reference "Test payment"
- [ ] Optionally link to the January 2025 invoice
- [ ] Verify payment appears in the list
- [ ] Delete the payment — confirm the dialog — verify it disappears

#### T9 — Settings

- [ ] Go to "Einstellungen"
- [ ] Change the client name to "Test Name", click Speichern
- [ ] Reload the page — verify the name persists
- [ ] Change it back to the original name
- [ ] Click a line item row, edit the label, save — verify the change sticks

#### T10 — Invoice Regeneration

- [ ] Go to Rechnungen, click on a draft invoice
- [ ] Click "Neu generieren"
- [ ] Confirm the dialog
- [ ] Verify a new PDF is generated (filename should stay the same, content recalculated)

#### T11 — Status Workflow

- [ ] On an invoice detail page, change status from "Entwurf" (draft) to "Versendet" (sent)
- [ ] Verify the badge updates to blue
- [ ] Change status to "Bezahlt" (paid)
- [ ] Verify the badge updates to green

#### T12 — PDF Verification

- [ ] Open a downloaded PDF
- [ ] Verify it contains: invoice number, service period, all line items with amounts, net/VAT/gross totals, company address, bank details in footer
- [ ] Compare layout against `docs/reference-docs/AR202506-02.docx` for visual consistency
