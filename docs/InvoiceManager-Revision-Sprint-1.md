# InvoiceManager — Revision Sprint 1

> **Context:** This document describes improvements for the existing Invoice Manager web application. The app was built from the `BLUEPRINT-Invoice-Manager.md` specification and is functional but has bugs and missing features identified during a manual UI review. This sprint focuses on bug fixes, document management, and laying the groundwork for multi-client support.
>
> **Stack:** React/TypeScript frontend (Vite, port 5173) + FastAPI/Python backend (port 8000) + SQLite database
>
> **Date:** 2026-02-28

---

## How to Use This Document

Each task below is self-contained with a clear description of the current behavior, expected behavior, and implementation guidance. Tasks are ordered by priority. Complete them in order — some later tasks depend on earlier fixes.

The existing `BLUEPRINT-Invoice-Manager.md` in the project root remains the canonical reference for data model, business rules, and overall architecture. This document describes only the delta.

---

## Task 1: Fix German Umlaut Encoding in Frontend

**Priority:** Critical — broken text visible on nearly every page

### Current Behavior

Hardcoded German UI strings render as literal escape sequences instead of actual characters. Examples:

| What renders | What it should say |
|---|---|
| `f\u00FCr` | für |
| `W\u00E4hrung` | Währung |
| `Kategorie f\u00FCr Import` | Kategorie für Import |
| `Positionen pr\u00FCfen` | Positionen prüfen |
| `\u00FCberschreiben` | überschreiben |
| `Zur\u00FCck` | Zurück |
| `Bank-Schl\u00FCsselw\u00F6rter` | Bank-Schlüsselwörter |

### Root Cause

The backend API returns proper UTF-8 (confirmed: dynamic data like `Österreich` displays correctly). The problem is in the **frontend source code** — the hardcoded UI labels contain double-escaped Unicode sequences (`\\u00FC`) that are treated as literal text, not as Unicode characters.

### What to Do

1. Search all `.tsx`, `.ts`, and `.json` files in the frontend `src/` directory for the regex pattern `\\u00[0-9a-fA-F]{2}`
2. Replace every occurrence with the actual UTF-8 character:
   - `\u00E4` → `ä`
   - `\u00F6` → `ö`
   - `\u00FC` → `ü`
   - `\u00C4` → `Ä`
   - `\u00D6` → `Ö`
   - `\u00DC` → `Ü`
   - `\u00DF` → `ß`
3. Ensure all source files are saved as UTF-8 (they should already be)
4. Verify by visiting every page: Dashboard, Rechnungen, Rechnung erstellen, Lieferantenrechnungen, Bank, Upwork, Zahlungen, Abstimmung, Kategorien (list + detail), Einstellungen

### Acceptance Criteria

- No `\u00XX` sequences visible anywhere in the rendered UI
- All German text displays with correct Umlaute and ß

---

## Task 2: Fix Document Download (404 Error)

**Priority:** Critical — core feature is broken

### Current Behavior

`GET /api/provider-invoices/{id}/download` returns HTTP 404 with `{"detail":"PDF file not found"}` even for invoices that have a `file_path` value in the database (e.g. `categories/junior_fm/ER2512-21.pdf`).

### Root Cause

The seed data in the database references file paths like `categories/junior_fm/ER2512-21.pdf`, but the actual PDF files exist in the original provider folders on disk:
- `Junior FM/ER2501-19.pdf` through `ER2512-21.pdf`
- `Kaletsch - Cloud engineer/` contains quarterly invoices
- `Aeologic/` contains USD invoices

The backend's storage/upload directory either does not contain these files or uses a different path convention.

### What to Do

1. **Check the backend config** for `UPLOAD_DIR`, `STORAGE_DIR`, or `MEDIA_ROOT` — determine where the backend expects files to be
2. **Option A (preferred):** Create the expected directory structure and copy/symlink the existing PDFs into it:
   ```
   {STORAGE_DIR}/categories/junior_fm/ER2501-19.pdf
   {STORAGE_DIR}/categories/junior_fm/ER2502-17.pdf
   ... etc.
   {STORAGE_DIR}/categories/cloud_engineer/INV307.pdf
   ... etc.
   {STORAGE_DIR}/categories/aeologic/AEO000716.pdf
   ... etc.
   ```
3. **Option B:** Update the `file_path` values in the database to match where the files actually are
4. **Add a startup validation** in the backend that logs a warning for any `provider_invoice` record where `file_path` is set but the file does not exist on disk
5. Test downloading at least one file from each category (Junior FM, Cloud Engineer, Aeologic)

### Acceptance Criteria

- Clicking "Download" on a Junior FM invoice downloads the actual PDF
- The browser receives `Content-Type: application/pdf` with correct `Content-Disposition` header
- Invoices with `file_path = null` show no Download link (current behavior is fine)

---

## Task 3: Add Document Upload UI for Provider Invoices

**Priority:** High — the backend endpoint exists but is not wired up in the frontend

### Current Behavior

The backend exposes `POST /api/provider-invoices/{id}/upload` but the frontend has no upload button. Invoices without a file show `-` in the PDF column with no way to attach a document.

### What to Build

On the **Lieferantenrechnungen** page (`/provider-invoices`):

1. For invoices where `file_path` is `null`: show an **upload icon/button** (e.g. a paperclip or upload arrow) in the PDF column instead of `-`
2. For invoices where `file_path` is set: show a **download icon** and a small **replace icon** (e.g. a refresh arrow)
3. Clicking the upload icon opens a file picker (accept `.pdf` only)
4. On file select, `POST` the file as `multipart/form-data` to `/api/provider-invoices/{id}/upload`
5. On success, refresh the row to show the download link
6. Show a toast notification on success/error

On the **Kategorie-Detail** page (e.g. `/categories/junior_fm`):

7. In the Lieferantenrechnungen table on this page, add the same upload/download icons per row
8. Add a **bulk upload** drop zone at the top: "PDFs hierher ziehen" — when files are dropped, try to match each filename to an existing invoice (by invoice number) and auto-upload. Show a summary of matches and misses.

### Acceptance Criteria

- User can upload a PDF to any provider invoice from both the list page and the category detail page
- After upload, the file_path is set and download works immediately
- Bulk upload from category detail matches files to invoices by filename

---

## Task 4: Add In-Browser Document Preview

**Priority:** High — users need to see documents without downloading

### What to Build

1. Add a **preview modal/drawer** that opens when clicking a filename or preview icon
2. Use `<iframe src="/api/provider-invoices/{id}/download" />` or a library like `react-pdf` to render the PDF inline
3. The modal should have:
   - A title bar showing the invoice number and category
   - A close button
   - A "Download" button to save the file locally
   - Navigation arrows if browsing from a list (optional, nice-to-have)
4. Apply the same preview capability to **generated invoices** (`/api/invoices/{id}/download`)

### Where to Add Preview Triggers

| Page | Trigger |
|---|---|
| Lieferantenrechnungen | Click on invoice number or a preview icon in the PDF column |
| Kategorie-Detail | Click on invoice number in the invoices table |
| Rechnungen (generated invoices list) | Click on invoice number or a preview icon |

### Acceptance Criteria

- Clicking an invoice number with an attached PDF opens a modal showing the PDF inline
- The modal has a download button
- Preview works for both provider invoices and generated invoices

---

## Task 5: Add Dokumente (Documents) Page

**Priority:** Medium — central document access across all categories

### What to Build

Add a new page at route `/documents` with a sidebar nav entry **"Dokumente"** (icon: folder or file).

This page shows **all uploaded files** across all categories and invoice types in a single searchable, filterable list.

#### Table Columns

| Column | Description |
|---|---|
| Dateiname | Original filename (linked to preview) |
| Typ | `Lieferantenrechnung`, `Bankbeleg`, `Ausgangsrechnung` |
| Kategorie | Cost category name (for provider invoices) or client name (for generated invoices) |
| Rechnungsnr. | Linked invoice number |
| Datum | Invoice date |
| Hochgeladen am | Upload timestamp |
| Aktionen | Preview, Download, Delete |

#### Filters

- By document type (provider invoice / generated invoice / bank statement)
- By category
- By date range
- Free text search on filename and invoice number

#### Additional Features

- Show total document count and total file size
- Flag orphaned files (files on disk not linked to any invoice record) if any exist

### Sidebar Navigation

Insert "Dokumente" between "Lieferantenrechnungen" and "Bank" in the sidebar.

### Acceptance Criteria

- All uploaded documents are visible in one central list
- Filters work correctly
- Preview and download work from this page
- Sidebar navigation is updated

---

## Task 6: Multi-Client Foundation

**Priority:** Medium — not blocking daily use, but architecturally important

### Current State

The app currently has a single-client assumption:
- Einstellungen page shows one client's data (DRS Holding AG) as global settings
- Line item definitions (`Rechnungspositionen`) are global, not scoped to a client
- The backend already has `GET/POST /api/clients` endpoints and the "Rechnung erstellen" page has a client dropdown — so partial multi-client awareness exists in the backend

### What to Change

#### 6a. Add Kunden (Clients) Page

Add a new page at route `/clients` with sidebar nav entry **"Kunden"** (icon: people/building).

**List view** showing all clients with columns: Name, Kundennummer, Stadt, Aktiv, Anzahl Rechnungen.

**Detail/Edit view** at `/clients/{id}` with all client fields:
- Name (Firmenname)
- Kundennummer (used in invoice numbering, e.g. `02`)
- Adresse (Straße)
- Adresse 2 (optional, Zusatz)
- PLZ / Stadt
- Land (default: Deutschland)
- USt-IdNr.
- Ansprechpartner (optional)
- E-Mail (optional)
- Zahlungsziel in Tagen (default: 14)
- Notizen (optional)
- Aktiv (boolean)

**CRUD:** Create, read, update. No delete — use "Aktiv = false" to retire a client.

Seed the existing DRS Holding AG data as the first client.

#### 6b. Restructure Einstellungen

Split the current Einstellungen page into two sections:

**Section 1: Unternehmensdaten (Company/Sender Data)**
- Firmenname: 29ventures GmbH
- Adresse
- PLZ / Stadt
- Geschäftsführer
- Steuernummer
- USt-IdNr.
- Bankverbindung (IBAN, BIC, Bank)
- E-Mail, Telefon, Website

This is your own company data that appears as the sender on invoices.

**Section 2: Rechnungspositionen**
- Keep the existing line item definitions table
- Add a **client dropdown filter** at the top — line items are per-client
- When a new client is added, they start with zero line items that must be configured

Remove the "Kundendaten" section (it now lives in the Kunden page).

#### 6c. Wire up Client Scoping

- On "Rechnung erstellen": the client dropdown already exists — ensure it loads from `/api/clients` and filters line item definitions by the selected client
- On the Rechnungen list: add a client filter column/dropdown
- On the Dashboard: add client selector (can default to most-active client)

### Backend Changes

- If the `clients` table already exists (which the API suggests), no schema changes are needed
- If `line_item_definitions` does not yet have a `client_id` foreign key, add it and migrate existing records to point to the DRS client
- Add a `company_settings` table or config section for the sender data (alternatively, store it in a settings JSON on disk)

### Sidebar Navigation

Insert "Kunden" above "Kategorien" in the sidebar. New order:
1. Dashboard
2. Rechnungen
3. Rechnung erstellen
4. Abstimmung
5. **Kunden** ← new
6. Kategorien
7. Dokumente ← new (from Task 5)
8. Lieferantenrechnungen
9. Bank
10. Upwork
11. Zahlungen
12. Einstellungen

### Acceptance Criteria

- Clients are fully manageable via the UI (add, edit, deactivate)
- DRS Holding AG is pre-populated as the initial client
- Einstellungen shows sender/company data separately from client data
- Line item definitions are filterable by client
- Invoice generation uses the selected client's data

---

## Task 7: UX Polish (Batch)

**Priority:** Low — individual items are small but improve overall quality

### 7a. Number Formatting in Einstellungen

The Rechnungspositionen table shows amounts as `16450.00` (English). Change to German format: `16.450,00 €`.

### 7b. Currency-Aware Amount Display

On the Lieferantenrechnungen page, amounts for USD invoices show `€` symbol. Change to show the correct currency symbol matching the `currency` field (`$` for USD, `€` for EUR). The column header should just say "Betrag" without a currency symbol.

### 7c. Bank Description Tooltip

On the Banktransaktionen page, truncated descriptions (ending with `...`) should show the full text in a tooltip on hover. Use a simple `title` attribute or a styled tooltip component.

### 7d. Dashboard Smart Default

The Dashboard defaults to the current month (February 2026) which has no data. Instead:
- Default to the most recent month that has either generated invoices or provider invoice data
- If no data exists at all, show the current month with a helpful empty state message

### 7e. Invoice Date Default

On "Rechnung erstellen", the Rechnungsdatum defaults to today. Instead, default to the last day of the selected invoice month (e.g. selecting Juni 2025 → defaults to 30.06.2025). The user can still override it.

### 7f. Category Row Hover

On the Kostenkategorien page, add a hover effect (e.g. background color change, cursor pointer) to indicate rows are clickable.

### 7g. Category Detail — Edit Mode

On the Kategorie-Detail page (`/categories/{id}`), add a "Bearbeiten" button that toggles fields into edit mode. Editable fields: name, provider_name, provider_location, bank_keywords, billing_cycle, cost_type, active. Save via `PATCH /api/cost-categories/{id}`.

### 7h. Provider Invoice CRUD

On the Lieferantenrechnungen page:
- Add a "Neue Rechnung" button → opens a form to manually create a provider invoice entry (category, number, date, amount, currency)
- Add an "Aktionen" column with Edit and Delete icons per row
- Clicking a row opens a detail/edit view

### Acceptance Criteria

Each sub-task above is independently testable. All German-facing number formats should be consistent (`1.234,56 €`). Interactive elements should have appropriate hover/focus states.

---

## Reference: Existing API Endpoints

These endpoints already exist in the backend (FastAPI, port 8000). Use them — avoid creating redundant endpoints.

```
GET/POST     /api/clients
GET/PATCH    /api/clients/{client_id}

GET/POST     /api/cost-categories
GET/PATCH    /api/cost-categories/{category_id}

GET/POST     /api/line-item-definitions
GET/PATCH/DEL /api/line-item-definitions/{definition_id}

GET/POST     /api/provider-invoices
GET/PATCH/DEL /api/provider-invoices/{invoice_id}
POST         /api/provider-invoices/{invoice_id}/upload    ← exists, not used in UI
GET          /api/provider-invoices/{invoice_id}/download  ← exists, broken (Task 2)

POST         /api/bank-transactions/import
GET/POST     /api/bank-transactions
GET/PATCH    /api/bank-transactions/{tx_id}

POST         /api/upwork-transactions/import
GET          /api/upwork-transactions
GET/PATCH    /api/upwork-transactions/{tx_id}

GET/POST     /api/invoices
GET          /api/invoices/{invoice_id}
POST         /api/invoices/preview
GET          /api/invoices/{invoice_id}/download
POST         /api/invoices/{invoice_id}/regenerate
PATCH        /api/invoices/{invoice_id}/status

GET/POST     /api/payments
GET/PATCH/DEL /api/payments/{payment_id}

GET          /api/working-days/{year}/{month}
GET          /api/dashboard/monthly/{year}/{month}
GET          /api/dashboard/open-invoices
GET          /api/dashboard/reconciliation/{year}/{month}
GET/POST     /api/backups
GET          /api/health
```

### Endpoints That May Need to Be Added

| Endpoint | Purpose | For Task |
|---|---|---|
| `GET /api/documents` | List all uploaded files across all types | Task 5 |
| `DELETE /api/cost-categories/{id}` | Delete a category | Task 7g |
| `GET/PATCH /api/settings/company` | Company/sender settings CRUD | Task 6b |

---

## Testing Checklist

After completing all tasks, verify:

- [ ] No `\u00XX` escape sequences visible anywhere in the UI
- [ ] Download works for Junior FM, Cloud Engineer, and Aeologic PDFs
- [ ] Upload works from Lieferantenrechnungen and Kategorie-Detail
- [ ] PDF preview opens inline for provider invoices and generated invoices
- [ ] Dokumente page shows all files with working filters
- [ ] Kunden page shows DRS Holding AG, allows editing and adding new clients
- [ ] Einstellungen shows company (sender) data, no longer shows client data
- [ ] Line item definitions are scoped to selected client
- [ ] Invoice generation uses correct client data
- [ ] All amounts use German formatting (1.234,56 €)
- [ ] USD invoices show $ symbol, not €
- [ ] Bank descriptions show full text on hover
- [ ] Dashboard defaults to last month with data
- [ ] Invoice date defaults to end of selected month
- [ ] Category rows have hover effect
- [ ] Category detail has edit mode
- [ ] Provider invoices have CRUD actions
