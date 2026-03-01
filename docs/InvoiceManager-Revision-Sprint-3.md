# Invoice Manager — Sprint 2 Review Summary (Rev. 2)

> **Reviewer:** Claude (AI Review)
> **Date:** 2026-03-01 (second review pass)
> **Previous Review:** 2026-02-28
> **Reference:** `InvoiceManager-Revision-Sprint-2.md`

---

## Executive Summary

This is the **second review pass** of Sprint 2. All 5 bugs identified in the initial review on 2026-02-28 remain **unfixed**. No changes were detected between the two reviews. The overall assessment is unchanged.

**Overall completion: ~75%** — strong foundation, 5 open bugs blocking full completion.

### Change Log (Rev. 1 → Rev. 2)

| Item                       | Rev. 1 (Feb 28) | Rev. 2 (Mar 1) | Change                                                      |
| -------------------------- | --------------- | -------------- | ----------------------------------------------------------- |
| PDF Preview Blank          | ❌               | ❌              | No change — deeper root cause identified (intermittent 503) |
| Currency Symbol € for USD  | ❌               | ❌              | No change                                                   |
| Abstimmung Missing Non-EUR | ❌               | ❌              | No change                                                   |
| Smart Month Default        | ❌               | ❌              | No change (now defaults to März 2026 instead of Feb 2026)   |
| Line Item Client Scoping   | ❌               | ❌              | No change                                                   |

---

## Task-by-Task Review

### Task 1: Fix Document Download (404 Error) — ✅ FIXED / Preview ❌

The download endpoint `GET /api/provider-invoices/{id}/download` returns HTTP 200 with `Content-Type: application/pdf` and valid PDF binary content. Download button works correctly.

**PDF Preview Still Broken:** The modal opens with a title bar (invoice number, "Herunterladen" and "Schließen" buttons) but the inline PDF area is blank white.

**Root Cause Analysis (Rev. 2):**

- The iframe `src` is set to `/api/provider-invoices/{id}/download` (relative URL) — this is correct
- The Vite proxy forwards the request to the backend — verified via `fetch()` returning status 200 with `application/pdf`
- Iframe dimensions are correct (853px × 1265px, `flex-1` in a flex-column parent)
- **Key finding:** Network monitoring revealed the download endpoint **intermittently returns HTTP 503**. When the iframe loads during a 503 response, Chrome displays blank white and does not auto-retry
- The 503 likely comes from the backend's file serving logic or a race condition with concurrent requests

**Recommended Fix:** Add retry logic or use `<object>` / `<embed>` tag with fallback. Alternatively, investigate why the backend returns 503 intermittently — likely a file handle or database connection issue.

**Verdict:** Download ✅ | Preview ❌

---

### Task 2: Bulk Upload with Auto-Record Creation — ✅ Mostly Complete

| Sub-Task                            | Status | Details                                                                                                                     |
| ----------------------------------- | ------ | --------------------------------------------------------------------------------------------------------------------------- |
| **2a. Bulk Upload UI**              | ✅      | Drag-and-drop zone on Lieferantenrechnungen: *"PDF-Rechnungen hierher ziehen oder klicken zum Auswählen (Mehrfachauswahl)"* |
| **2b. PDF Text Extraction Backend** | ✅      | `POST /api/provider-invoices/bulk-upload` and `bulk-confirm` endpoints exist                                                |
| **2c. MCP Endpoint**                | ⚠️     | Cannot verify from browser — needs Claude Cowork / MCP server inspection                                                    |
| **2d. Category Detail Upload**      | ✅      | Aeologic category detail page has scoped drag-and-drop upload zone                                                          |

**Verdict:** UI and endpoints in place ✅ | E2E flow and MCP tools need verification ⚠️

---

### Task 3: Bidirectional Transaction Matching — Partially Complete

| Sub-Task                       | Status | Details                                                                                                |
| ------------------------------ | ------ | ------------------------------------------------------------------------------------------------------ |
| **3a/3b. Auto-Matching Logic** | ✅      | "Zugeordnet" column on Lieferantenrechnungen shows matched months. Match/manual-match endpoints exist. |
| **3c. Matching Review UI**     | ✅      | Abstimmung has "Offene Zuordnungen" with "Unbezahlte Rechnungen" and comparison table                  |
| **3d. Data Model Changes**     | ✅      | New columns visible: payment status, matched transaction references, category assignments              |

**Bug (unchanged):** Abstimmung only shows EUR invoices (Junior FM) per month. Aeologic USD invoices and cloud_engineer invoices do not appear. Tested October 2025 — only Junior FM 10/2025 visible, despite Aeologic AEO000828 ($1,246, dated 31.10.2025) existing in the provider invoices table.

**Likely cause:** Reconciliation logic filters by `covers_months` field, which Aeologic invoices don't have populated.

**Verdict:** Infrastructure ✅ | Incomplete for non-EUR / non-monthly invoices ❌

---

### Task 4: Currency Conversion and Banking Fee Tracking — Mostly Complete

| Sub-Task                          | Status | Details                                                                                                           |
| --------------------------------- | ------ | ----------------------------------------------------------------------------------------------------------------- |
| **4a. Fee Calculation Logic**     | ⚠️     | Backend logic exists, not testable without confirming matches                                                     |
| **4b. UI for Fee Tracking**       | ⚠️     | Match confirmation dialog not tested                                                                              |
| **4c. Cost Breakdown Visibility** | ✅      | Kostenübersicht on Aeologic: Rechnung, Monat, Betrag (USD), Bank (EUR), FX-Kurs, Bankgebühr. Avg FX rate Ø 1.2639 |
| **4d. Invoice Generation Impact** | ⚠️     | Not tested                                                                                                        |

**Bug (unchanged):** "Betrag (USD)" column and main invoice table on category detail show `€` symbol instead of `$` for Aeologic invoices (e.g., `1.302,00 €` should be `1.302,00 $`). The main Lieferantenrechnungen list page displays the correct `$` symbol — so the currency formatting function exists but isn't being applied on category detail views.

**Verdict:** Cost breakdown exists ✅ | Currency symbol bug ❌ | Match flow untested ⚠️

---

### Task 5: Improved Reconciliation Dashboard — Partially Complete

| Section                        | Status | Details                                                                                        |
| ------------------------------ | ------ | ---------------------------------------------------------------------------------------------- |
| **Monatsübersicht**            | ✅      | Summary cards: Rechnungen, Abgeglichen (X von Y), Vorgeschlagen, Offen (Bank), Rechnungsstatus |
| **Offene Zuordnungen**         | ✅      | "Unbezahlte Rechnungen" with invoice details and comparison table                              |
| **Abgeschlossene Zuordnungen** | ⚠️     | Not visible (likely because no matches confirmed yet)                                          |

**Bug (unchanged):** Defaults to current month (now März 2026, previously Feb 2026) with zero data. Should auto-detect and navigate to the most recent month with data.

**Note:** Reconciliation API is at `/api/dashboard/reconciliation/{year}/{month}` (200) rather than `/api/reconciliation/{year}/{month}` (404) — functional but doesn't match spec.

**Verdict:** Good progress ✅ | Missing smart default ❌ | Only EUR invoices ❌

---

### Task 6: UX Polish — Sprint 1 Carry-Overs

| Sub-Task                         | Status | Details                                                                       |
| -------------------------------- | ------ | ----------------------------------------------------------------------------- |
| **6a. Bank Description Tooltip** | ✅      | `title` attribute set, CSS `text-overflow: ellipsis`, native tooltip on hover |
| **6b. Dashboard Smart Default**  | ❌      | Still defaults to current month (März 2026) with all zeros                    |
| **6c. Invoice Date Default**     | ⚠️     | Not testable without full invoice generation flow                             |
| **6d. Category Row Hover**       | ✅      | `cursor-pointer` + `hover:bg-gray-50` CSS classes                             |
| **6e. Line Item Client Scoping** | ❌      | No client dropdown in Rechnungspositionen (Einstellungen)                     |
| **6f. "Neue Position" Button**   | ✅      | Present in Rechnungspositionen section                                        |

---

## Open Bugs — Priority Order

### 1. PDF Preview Blank (P1 — Usability)

- **What:** Modal opens but shows blank white area instead of PDF content
- **Where:** Any provider invoice preview (e.g., click invoice number link)
- **Root Cause:** Backend intermittently returns HTTP 503 for download endpoint; when iframe loads during 503, Chrome shows blank and doesn't retry
- **Fix Options:**
  - Investigate and fix the backend 503 intermittent issue (likely file handle / connection problem)
  - Add frontend retry logic for failed iframe loads
  - Switch from `<iframe>` to `<object>` or `<embed>` with fallback
  - Use a library like `react-pdf` / `@react-pdf-viewer/core`
  - Ensure `Content-Disposition: inline` header is set

### 2. Currency Symbol on Category Detail (P2 — Data Accuracy)

- **What:** Aeologic USD amounts display with `€` instead of `$`
- **Where:** Category detail page — both main invoice table and Kostenübersicht
- **Not Affected:** Lieferantenrechnungen list page (shows correct `$`)
- **Fix:** The category detail component needs to use the invoice's `currency` field when formatting amounts, not hardcode `€`

### 3. Abstimmung Missing Non-EUR Invoices (P2 — Functional Gap)

- **What:** Only Junior FM (EUR, monthly) invoices appear in reconciliation view
- **Where:** Abstimmung page — any month
- **Impact:** Reconciliation is incomplete without Aeologic (USD) and cloud_engineer entries
- **Fix:** Filter invoices by `invoice_date` falling within the selected month, not by `covers_months` field

### 4. Dashboard/Abstimmung Smart Default (P3 — UX)

- **What:** Both pages default to current month (März 2026) which has no data
- **Where:** Dashboard and Abstimmung page load
- **Impact:** Users must manually navigate backward to find data (currently December 2025)
- **Fix:** Query for the most recent month with data and default to that; show empty state message with quick link if current month has no data

### 5. Line Item Client Scoping (P3 — Feature Gap)

- **What:** No client dropdown filter in Rechnungspositionen settings
- **Where:** Einstellungen → Rechnungspositionen section
- **Impact:** Cannot configure different line items per client for multi-client invoice generation
- **Fix:** Add a client selector dropdown above the line items list; filter/scope items per selected client

---

## What's Working Well

1. **Sidebar navigation** — clean, well-organized, all links route correctly
2. **Einstellungen** — company data (Unternehmensdaten) cleanly separated and populated
3. **Kunden page** — DRS Holding AG pre-populated, "Neuer Kunde" button available
4. **German number formatting** — consistent throughout (`16.450,00 €`, `8.553,60 €`)
5. **Provider invoice CRUD** — Bearbeiten, Löschen, and "Neue Rechnung" all present
6. **Upload/Download UI** — "Hochladen" for missing, "Download" + "Ersetzen" for existing
7. **Dashboard reconciliation widget** — summary cards with quick-action buttons
8. **Bank XLSX import** — drag-and-drop import zone on Banktransaktionen page
9. **Kostenübersicht** — FX cost breakdown table on Aeologic category detail
10. **Bulk upload drop zones** — present on both Lieferantenrechnungen and category detail pages

---

## Testing Checklist

| #   | Check                                            | Status                              |
| --- | ------------------------------------------------ | ----------------------------------- |
| 1   | Download works for provider invoices             | ✅ API returns valid PDF             |
| 2   | Preview modal shows PDF content                  | ❌ Blank (intermittent 503)          |
| 3   | Bulk PDF upload extracts metadata                | ⚠️ UI present, not tested E2E       |
| 4   | Review table after upload allows editing         | ⚠️ Not tested                       |
| 5   | MCP tools create provider invoice records        | ⚠️ Not verified                     |
| 6   | Bank import auto-matches transactions            | ⚠️ Not tested                       |
| 7   | Invoice creation auto-matches to transactions    | ⚠️ Not tested                       |
| 8   | Abstimmung shows unmatched items both directions | ✅ Shows unbezahlte Rechnungen       |
| 9   | Confirming a match calculates FX rate            | ⚠️ Not tested                       |
| 10  | Invoice generation uses amount_eur for FX        | ⚠️ Not tested                       |
| 11  | Distributed costs use bank payment as base       | ⚠️ Not tested                       |
| 12  | Category detail shows FX cost breakdown          | ✅ Kostenübersicht visible           |
| 13  | Bank description tooltips show full text         | ✅ Title attribute set               |
| 14  | Dashboard defaults to recent month with data     | ❌ Defaults to current month         |
| 15  | Invoice date defaults to end of month            | ⚠️ Not tested                       |
| 16  | Category rows have hover effect                  | ✅ cursor-pointer + hover:bg-gray-50 |
| 17  | Line items filterable by client                  | ❌ No client dropdown                |

---

## Next Steps for Sprint 3

The 5 open bugs should be resolved before adding new features. Suggested sprint scope:

1. **Fix the 5 open bugs** listed above (estimated: 1–2 days)
2. **End-to-end testing** of bulk upload flow with actual PDF files
3. **End-to-end testing** of transaction matching (confirm a match, verify FX calculation)
4. **MCP tool verification** from a Claude Cowork session
5. After bugs are resolved: proceed with invoice generation flow testing
