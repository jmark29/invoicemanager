# Task: Import Existing Invoices + Month-by-Month Catch-Up Generation

> **Priority:** P1 (Foundation — system needs awareness of past invoices)
> **Estimated effort:** 6–8 hours
> **Dependencies:** None (can run in parallel with bug fixes)

---

## Problem

The Invoice Manager has no record of invoices already issued. Jan has created invoices for Jan–Jun 2025 as .docx files (AR202501-02 through AR202506-02). The system needs to:

1. **Import** these existing invoices so it knows what's been billed
2. **Enable catch-up generation** for Jul–Dec 2025 (and beyond), triggered manually month by month with a preview step

Without this, the system can't accurately track receivables, reconcile payments, or know which months still need invoicing.

---

## Part 1: Import Existing Invoices

### 1a. Upload UI

Add an **"Importieren"** button next to "Neue Rechnung" on the Rechnungen page. Clicking it opens a modal or page with:

- Drag-and-drop zone accepting `.docx` and `.pdf` files (single or multiple)
- Label: *"Bestehende Rechnungen importieren (DOCX/PDF)"*

### 1b. Document Parsing (Backend)

Create endpoint `POST /api/invoices/import` that:

1. Accepts uploaded .docx (or .pdf) files
2. Extracts structured data using text parsing:
   - **Invoice number** → from "Rechnung XXXXXX-XX" line
   - **Invoice date** → from the date line (e.g., "Wiesbaden, 28.02.2025")
   - **Service period** → from "Leistungszeitraum DD.MM.YYYY bis DD.MM.YYYY"
   - **Client** → from recipient block (first line, e.g., "DRS Holding AG")
   - **Line items** → each row with Pos, Bezeichnung, Betrag
   - **Totals** → Netto, USt (rate + amount), Brutto

#### Expected Extraction Format

```json
{
  "invoice_number": "202501-02",
  "invoice_date": "2025-02-28",
  "period_start": "2025-01-01",
  "period_end": "2025-01-31",
  "client_name": "DRS Holding AG",
  "line_items": [
    { "position": 1, "description": "Team- & Projektmanagement und Konzeption", "amount": 16450.00 },
    { "position": 2, "description": "Senior FileMaker Entwickler", "amount": 8300.00 },
    { "position": 3, "description": "Junior FileMaker Entwickler", "amount": 1300.00 },
    { "position": 4, "description": "Serveradministration und AWS-Services", "amount": 2851.20 },
    { "position": 5, "description": "Mobile Softwareentwickler", "amount": 5083.19 },
    { "position": 6, "description": "2. Mobile Softwareentwickler, QA- und Business Analyst Services", "amount": 1551.41 }
  ],
  "net_total": 35535.80,
  "tax_rate": 19,
  "tax_amount": 6751.80,
  "gross_total": 42287.60
}
```

### 1c. Review & Confirm UI

After parsing, show a **review table** (similar to bulk upload for provider invoices):

| Field | Extracted Value | Editable? |
|-------|----------------|-----------|
| Rechnungsnummer | 202501-02 | Yes |
| Datum | 28.02.2025 | Yes |
| Leistungszeitraum | 01.01.2025 – 31.01.2025 | Yes |
| Kunde | DRS Holding AG | Yes (dropdown) |
| Status | Versendet | Yes (dropdown: Entwurf, Versendet, Bezahlt) |

Line items table showing Pos, Bezeichnung, Betrag — all editable.

Totals auto-calculated from line items.

**"Importieren"** button saves to database.

### 1d. Data Model

#### `invoices` Table (Header Data)

Imported invoices use the **same `invoices` table** as generated ones. New/modified columns:

```sql
ALTER TABLE invoices ADD COLUMN source TEXT DEFAULT 'generated';
-- Values: 'generated' (created by system), 'imported' (uploaded existing)

ALTER TABLE invoices ADD COLUMN original_file TEXT;
-- Stores path to the original uploaded .docx/.pdf file

ALTER TABLE invoices ADD COLUMN status TEXT DEFAULT 'draft';
-- Values: 'draft' (Entwurf), 'sent' (Versendet), 'paid' (Bezahlt)
-- Imported invoices default to 'sent'
```

Existing columns used: `invoice_number`, `invoice_date`, `period_start`, `period_end`, `client_id`, `net_total`, `tax_rate`, `tax_amount`, `gross_total`.

#### `invoice_line_items` Table (NEW — Individual Positions)

Each line item is a **separate record** linked to the invoice:

```sql
CREATE TABLE invoice_line_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id INTEGER NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,              -- Pos number (1, 2, 3, ...)
    description TEXT NOT NULL,              -- "Junior FileMaker Entwickler"
    amount REAL NOT NULL,                   -- Net amount in EUR (e.g., 1300.00)

    -- Link to Rechnungsposition config (from Einstellungen)
    line_item_config_id INTEGER REFERENCES line_item_configs(id),

    -- Type inherited from config, or set manually
    type TEXT,                              -- 'fixed', 'category', 'manual'
    category_id TEXT,                       -- 'junior_fm', 'aeologic', etc.

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### `invoice_line_item_sources` Table (NEW — Traceability Links)

Links each line item to the provider invoice(s) that contributed to its amount:

```sql
CREATE TABLE invoice_line_item_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    line_item_id INTEGER NOT NULL REFERENCES invoice_line_items(id) ON DELETE CASCADE,
    provider_invoice_id INTEGER NOT NULL REFERENCES provider_invoices(id),
    amount_contributed REAL,               -- How much this provider invoice contributed
    -- e.g., if two Aeologic invoices sum to one line item,
    -- each gets its own record with its contribution amount

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Data Flow

```
Provider Invoice (Aeologic AEO000828, $1,246)
    ↓ (matched to bank transaction, amount_eur = 1.036,28 €)
invoice_line_item_sources (provider_invoice_id → AEO000828, amount = 1.036,28)
    ↓ (linked to)
invoice_line_items (Pos 6, "2. Mobile Softwareentwickler...", amount = 1.036,28 €)
    ↓ (belongs to)
invoices (AR202503-02, DRS Holding AG, März 2025)
```

When multiple provider invoices contribute to one line item (e.g., two Aeologic invoices in one month), the amounts are **summed** into a single line item, and both provider invoices are linked via `invoice_line_item_sources`.

### 1e. Line Item Matching

During import review, the system should **auto-match line item descriptions** to existing Rechnungspositionen from Einstellungen:

| Invoice Description | Matched Position | Category | Type |
|---|---|---|---|
| "Team- & Projektmanagement und Konzeption" | Pos 1 | — | fixed |
| "Senior FileMaker Entwickler" | Pos 2 | — | fixed |
| "Junior FileMaker Entwickler" | Pos 3 | junior_fm | category |
| "Serveradministration und AWS-Services" | Pos 4 | cloud_engineer | category |
| "Mobile Softwareentwickler" | Pos 5 | upwork_mobile | category |
| "2. Mobile Softwareentwickler, QA- und BA Services" | Pos 6 | aeologic | category |
| "Reisekosten" | Pos 7 | — | manual |

This matching populates `line_item_config_id`, `type`, and `category_id` on each imported line item.

For category-based line items, the system should also **auto-link to provider invoices** for that category and month via `invoice_line_item_sources`. For example, importing AR202501-02 with Pos 3 = 1.300,00 € (junior_fm, Jan 2025) would look up provider invoice "01/2025" (junior_fm, 1.300,00 €) and create the source link.

### 1f. Traceability View

After import, each invoice should have a detail view showing:

- All line items with their amounts
- For category-based items: linked provider invoice(s) with amounts
- Visual indicator: ✅ linked / ⚠️ no provider invoice found / ❌ amount mismatch

This enables the core verification: **every provider cost was passed through to the client**.

---

## Part 2: Cost Reconciliation — The Running Balance

### Core Concept

The system's primary job is to ensure that **every provider cost is eventually invoiced to the client** — not too little, not too much. This is tracked as a **running balance per category**:

```
Running Balance = Total provider costs received (EUR) − Total invoiced to client for that category
```

- **Balance > 0** → Under-invoiced: provider costs not yet passed through to client
- **Balance = 0** → Fully reconciled
- **Balance < 0** → Over-invoiced: more was billed than actually incurred

This balance is cumulative across ALL months — the system doesn't care which month a cost was invoiced in, only that it was invoiced at all.

### 2a. Kostenabgleich View (Cost Reconciliation)

New page or section (accessible from Dashboard or as a standalone page) showing a per-category running balance:

| Kategorie | Kosten Gesamt (EUR) | Berechnet Gesamt | Delta | Status |
|-----------|--------------------:|------------------:|------:|--------|
| junior_fm | 18.500,00 € | 18.500,00 € | 0,00 € | ✅ Ausgeglichen |
| cloud_engineer | 17.923,60 € | 17.104,40 € | 819,20 € | ⚠️ Noch nicht berechnet |
| aeologic | 32.450,00 € | 30.800,00 € | 1.650,00 € | ⚠️ Noch nicht berechnet |
| upwork_mobile | 22.100,00 € | 22.100,00 € | 0,00 € | ✅ Ausgeglichen |

**"Kosten Gesamt"** = Sum of all provider invoices for that category (using `amount_eur` for FX categories, `amount` for EUR categories)
**"Berechnet Gesamt"** = Sum of all line item amounts on outgoing invoices linked to that category (via `invoice_line_item_sources` or `category_id`)
**"Delta"** = Kosten − Berechnet (positive = un-invoiced costs remain)

Clicking a category row expands to show the detail:

| Provider Invoice | Datum | Betrag (EUR) | Berechnet auf Rechnung | Status |
|---|---|---:|---|---|
| 01/2025 (junior_fm) | 08.01.2025 | 1.300,00 € | AR202501-02, Pos 3 | ✅ |
| 02/2025 (junior_fm) | 10.02.2025 | 2.000,00 € | AR202502-02, Pos 3 | ✅ |
| AEO000828 | 31.10.2025 | 1.036,28 € | — | ❌ Nicht berechnet |

This makes it immediately visible which provider costs have been passed through and which haven't.

### 2b. Un-Invoiced Costs Feed into Invoice Generation

When generating a new invoice (whether catch-up or regular), the system assembles line items using the running balance:

1. **Fixed positions** (type: `fixed`) → Use configured amount directly (unchanged)

2. **Category-based positions** (type: `category`) → Instead of "provider costs for this month," use **un-invoiced provider costs for this category**:
   - Query: All provider invoices for category X where no `invoice_line_item_sources` record exists
   - Sum these into the line item amount
   - The preview shows which provider invoices will be included

3. **Manual positions** (type: `manual`) → User fills in amount

This approach naturally handles:
- **Missed months**: If an Aeologic invoice from July was skipped, it shows up as un-invoiced and gets suggested for the next invoice
- **Multiple invoices**: Two Aeologic invoices in one month get summed together
- **Timing flexibility**: A provider invoice from late October can be invoiced in November — the running balance doesn't care
- **Corrections**: If a previous invoice under-billed, the remaining cost surfaces automatically

### 2c. Invoice Generation Flow (Revised)

**Step 1 — Select Month**

Dashboard shows missing months indicator. User clicks a month (e.g., "Jul 2025").

**Step 2 — Line Item Assembly with Running Balance**

The system pre-fills line items:

| Pos | Bezeichnung | Typ | Betrag | Quelle |
|-----|------------|-----|-------:|--------|
| 1 | Team- & Projektmanagement | fixed | 16.450,00 € | Konfiguriert |
| 2 | Senior FileMaker Entwickler | fixed | 8.300,00 € | Konfiguriert |
| 3 | Junior FileMaker Entwickler | category | 1.600,00 € | 07/2025 (1.600,00 €) |
| 4 | Serveradministration und AWS-Services | category | 2.851,20 € | INV315 (2.851,20 €) |
| 5 | Mobile Softwareentwickler | category | 4.673,70 € | Upwork Jul 2025 (4.673,70 €) |
| 6 | 2. Mobile Softwareentwickler, QA- und BA | category | 3.170,48 € | AEO000802 (1.273,66 €) + AEO000789 (1.896,82 €) ⚠️ |

The ⚠️ on Pos 6 indicates these Aeologic invoices are from a different month (e.g., August) but were un-invoiced — the system suggests including them now.

The user can:
- Accept the suggested amounts
- Remove a provider invoice from a line item (defer to next month)
- Manually adjust amounts
- Add manual line items (e.g., Reisekosten)

**Step 3 — Preview & Confirm**

Full invoice preview with Net/Tax/Gross. "Rechnung erstellen" saves the record, creates `invoice_line_item_sources` links, and generates .docx.

After generation, the running balance for each affected category is updated (the delta shrinks or reaches zero).

**Step 4 — Next Month**

Offer to proceed to the next missing month. The line items for the next month will exclude costs just invoiced (since they now have source links).

---

## Part 3: Invoice Status Tracking

### 3a. Status Values

```
Entwurf → Versendet → Bezahlt
```

- **Entwurf** (Draft): Generated but not sent
- **Versendet** (Sent): Invoice sent to client
- **Bezahlt** (Paid): Payment received

Imported invoices default to **Versendet** (since they were already sent).
Newly generated invoices default to **Entwurf**.

### 3b. Status in UI

- Rechnungen list: Status column with colored badges
- Dashboard: "Offene Rechnungen" count = Versendet (not yet paid)
- Filter: Status dropdown on Rechnungen page (already exists)

---

## Part 4: Dashboard Integration

The Dashboard should surface the running balance prominently:

### Kostenabgleich Summary Card

```
Kostenabgleich
━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 2 Kategorien ausgeglichen
⚠️ 2 Kategorien offen (2.469,20 € nicht berechnet)
                                    [Details →]
```

### Missing Months Card (existing, refined)

```
Fehlende Rechnungen
━━━━━━━━━━━━━━━━━━━━━━━━━━
Jul 2025 · Aug 2025 · Sep 2025
Okt 2025 · Nov 2025 · Dez 2025
                    [Nächste erstellen →]
```

The "Nächste erstellen" button opens the generation flow for the earliest missing month with the running-balance-based line item assembly.

---

## Line Item Amount Sources — Summary

| Position | Type | Amount Source |
|----------|------|--------------|
| Team- & Projektmanagement | fixed | Configured amount (16.450,00 €) |
| Senior FileMaker Entwickler | fixed | Configured amount (8.300,00 €) |
| Junior FileMaker Entwickler | category (junior_fm) | Un-invoiced provider costs for junior_fm |
| Serveradministration und AWS-Services | category (cloud_engineer) | Un-invoiced provider costs for cloud_engineer (amount_eur) |
| Mobile Softwareentwickler | category (upwork_mobile) | Un-invoiced Upwork transactions |
| 2. Mobile Softwareentwickler, QA- und BA | category (aeologic) | Un-invoiced provider costs for aeologic (amount_eur) |
| Reisekosten | manual | User input |

**Key difference from previous approach:** Category amounts are not "costs for this specific month" but "all un-invoiced costs for this category." This ensures nothing falls through the cracks across months.

---

## Acceptance Criteria

### Import
- [ ] "Importieren" button on Rechnungen page
- [ ] .docx file upload and parsing works for all 6 sample invoices
- [ ] Review screen shows all extracted data correctly
- [ ] User can edit any field before confirming
- [ ] Line items auto-matched to Rechnungspositionen
- [ ] Imported line items auto-linked to provider invoices for same category/period
- [ ] Imported invoices appear in Rechnungen list with "Importiert" badge
- [ ] Original .docx file stored and accessible

### Cost Reconciliation (Running Balance)
- [ ] Kostenabgleich view shows per-category running balance
- [ ] Delta = total provider costs − total invoiced per category
- [ ] Drill-down shows individual provider invoices with linked/unlinked status
- [ ] ✅/⚠️/❌ indicators for reconciliation status
- [ ] Dashboard summary card shows count of reconciled vs. open categories

### Invoice Generation (Running-Balance-Based)
- [ ] Dashboard/Rechnungen shows missing months indicator
- [ ] Generation flow pre-fills category amounts from un-invoiced provider costs
- [ ] Preview shows which provider invoices contribute to each line item
- [ ] User can defer specific provider invoices to a later month
- [ ] Fixed positions show correct configured amounts
- [ ] Manual positions show empty field for user input
- [ ] Net/Tax/Gross auto-calculated
- [ ] Invoice number follows pattern YYYYMM-02
- [ ] "Rechnung erstellen" saves record, creates source links, generates .docx
- [ ] After generation, running balance is updated
- [ ] After generation, next missing month is offered

### Status Tracking
- [ ] Three statuses: Entwurf, Versendet, Bezahlt
- [ ] Imported invoices default to Versendet
- [ ] Generated invoices default to Entwurf
- [ ] Status filterable on Rechnungen page
- [ ] Dashboard shows count of open (Versendet) invoices
