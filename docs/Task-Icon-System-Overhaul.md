# Task: Icon System Overhaul — Replace Emoji & Text with Lucide Icons

> **Priority:** P3 (UX Polish)
> **Estimated effort:** 3–4 hours
> **Dependency:** `npm install lucide-react`

---

## Objective

Replace all emoji characters in the sidebar and all text-based action links in tables with proper SVG icons from **lucide-react**. This creates a more professional, consistent visual language across the app.

---

## 1. Install lucide-react

```bash
npm install lucide-react
```

Lucide is tree-shakeable — only icons actually imported are included in the bundle. No additional CSS or font files needed.

---

## 2. Sidebar Navigation — Replace Emoji with Lucide Icons

Each sidebar link currently uses a Unicode emoji in a `<span class="w-5 text-center">`. Replace the emoji character with a Lucide icon component (size 18, `className="w-5 h-5"`).

| Route                                        | Current Emoji | Lucide Icon       | Import                                           |
| -------------------------------------------- | ------------- | ----------------- | ------------------------------------------------ |
| `/` (Dashboard)                              | ⌂             | `LayoutDashboard` | `import { LayoutDashboard } from 'lucide-react'` |
| `/invoices` (Rechnungen)                     | 📄            | `FileText`        | `import { FileText } from 'lucide-react'`        |
| `/invoices/generate` (Rechnung erstellen)    | +             | `FilePlus`        | `import { FilePlus } from 'lucide-react'`        |
| `/reconciliation` (Abstimmung)               | ⚖             | `Scale`           | `import { Scale } from 'lucide-react'`           |
| `/clients` (Kunden)                          | 👤            | `Users`           | `import { Users } from 'lucide-react'`           |
| `/categories` (Kategorien)                   | ☰             | `LayoutList`      | `import { LayoutList } from 'lucide-react'`      |
| `/provider-invoices` (Lieferantenrechnungen) | 📥            | `FileDown`        | `import { FileDown } from 'lucide-react'`        |
| `/bank-transactions` (Bank)                  | 🏦            | `Landmark`        | `import { Landmark } from 'lucide-react'`        |
| `/upwork-transactions` (Upwork)              | 💻            | `Monitor`         | `import { Monitor } from 'lucide-react'`         |
| `/payments` (Zahlungen)                      | €             | `Euro`            | `import { Euro } from 'lucide-react'`            |
| `/settings` (Einstellungen)                  | ⚙             | `Settings`        | `import { Settings } from 'lucide-react'`        |

### Implementation

Replace:

```jsx
<span className="w-5 text-center">📄</span>Rechnungen
```

With:

```jsx
<FileText size={18} className="w-5 h-5 flex-shrink-0" />
<span>Rechnungen</span>
```

Use `text-gray-400` for inactive icons and `text-white` (or `text-blue-400`) for the active route icon.

---

## 3. Lieferantenrechnungen Table — Merge PDF + Aktionen into Single "Aktionen" Column

### Current State (two columns)

**PDF column:** Hochladen | Download + Ersetzen
**Aktionen column:** Bearbeiten + Löschen

### Target State (one column: "Aktionen")

Merge into a single column with icon buttons. Each icon has a `title` attribute for tooltip on hover.

| Action       | Condition       | Lucide Icon | Color           | Tooltip             |
| ------------ | --------------- | ----------- | --------------- | ------------------- |
| Upload PDF   | No PDF attached | `Upload`    | `text-blue-600` | "PDF hochladen"     |
| Download PDF | PDF exists      | `Download`  | `text-blue-600` | "PDF herunterladen" |
| Preview PDF  | PDF exists      | `Eye`       | `text-gray-600` | "Vorschau"          |
| Replace PDF  | PDF exists      | `RefreshCw` | `text-gray-500` | "PDF ersetzen"      |
| Edit         | Always          | `Pencil`    | `text-blue-600` | "Bearbeiten"        |
| Delete       | Always          | `Trash2`    | `text-red-600`  | "Löschen"           |

### Layout

```
┌──────────────────────────────────────┐
│ Aktionen                             │
├──────────────────────────────────────┤
│  ⬆  ✏️  🗑   (no PDF: upload, edit, delete)
│  ⬇  👁  🔄  ✏️  🗑   (has PDF: download, preview, replace, edit, delete)
└──────────────────────────────────────┘
```

### Implementation

```jsx
<td className="flex items-center gap-1.5">
  {invoice.has_pdf ? (
    <>
      <button title="PDF herunterladen" onClick={() => handleDownload(invoice.id)}>
        <Download size={16} className="text-blue-600 hover:text-blue-800" />
      </button>
      <button title="Vorschau" onClick={() => handlePreview(invoice.id)}>
        <Eye size={16} className="text-gray-600 hover:text-gray-800" />
      </button>
      <button title="PDF ersetzen" onClick={() => handleReplace(invoice.id)}>
        <RefreshCw size={16} className="text-gray-500 hover:text-gray-700" />
      </button>
    </>
  ) : (
    <button title="PDF hochladen" onClick={() => handleUpload(invoice.id)}>
      <Upload size={16} className="text-blue-600 hover:text-blue-800" />
    </button>
  )}
  <span className="mx-0.5" /> {/* small visual separator */}
  <button title="Bearbeiten" onClick={() => handleEdit(invoice.id)}>
    <Pencil size={16} className="text-blue-600 hover:text-blue-800" />
  </button>
  <button title="Löschen" onClick={() => handleDelete(invoice.id)}>
    <Trash2 size={16} className="text-red-600 hover:text-red-800" />
  </button>
</td>
```

---

## 4. Other Pages — Replace Text Actions with Icons

Apply the same pattern to any other table with text-based action links:

### Rechnungen (Invoices) Page

| Action       | Icon       | Notes         |
| ------------ | ---------- | ------------- |
| Download PDF | `Download` | If applicable |
| Preview      | `Eye`      | PDF preview   |
| Edit         | `Pencil`   | Edit invoice  |
| Delete       | `Trash2`   | Red color     |

### Bank Transactions Page

| Action     | Icon            | Notes                  |
| ---------- | --------------- | ---------------------- |
| View/match | `Link` or `Eye` | If match action exists |

### Kunden (Clients) Page

| Action | Icon     | Notes       |
| ------ | -------- | ----------- |
| Edit   | `Pencil` | Edit client |
| Delete | `Trash2` | Red color   |

### Einstellungen (Settings) Page

| Action          | Icon                | Notes                               |
| --------------- | ------------------- | ----------------------------------- |
| Edit position   | `Pencil`            | Edit line item                      |
| Delete position | `Trash2`            | Red color                           |
| Neue Position   | Keep as text button | Primary action buttons stay as text |

---

## 5. Primary Action Buttons — Keep as Text

Buttons like "Neue Rechnung", "Neuer Kunde", "Neue Position" should remain as **text buttons** (blue filled). These are primary actions that benefit from clear text labels. Don't replace these with icons.

---

## 6. Icon Style Guidelines

- **Size:** 16px for table action icons, 18px for sidebar icons
- **Stroke width:** Default (2px) — Lucide's default looks clean at these sizes
- **Colors:** Match current color scheme — `text-blue-600` for primary actions, `text-gray-500/600` for secondary, `text-red-600` for destructive
- **Hover:** Darken on hover (`hover:text-blue-800`, etc.)
- **Spacing:** `gap-1.5` (6px) between icon buttons in action columns
- **Tooltips:** Native `title` attribute on every icon button — essential for discoverability
- **Cursor:** `cursor-pointer` on all icon buttons
- **Hit area:** Minimum 28×28px touch target — use `p-1` padding on the button wrapper

---

## 7. Acceptance Criteria

- [ ] `lucide-react` installed as dependency
- [ ] All 11 sidebar items use Lucide icons (no emoji)
- [ ] Active sidebar item icon has distinct color
- [ ] Lieferantenrechnungen has single "Aktionen" column (no separate "PDF" column)
- [ ] All table actions use icon buttons with tooltips
- [ ] Icon tooltips show German text matching previous link labels
- [ ] No text-based action links remain in any table
- [ ] Primary action buttons ("Neue Rechnung", etc.) remain as text
- [ ] Icons are consistent in size and color across all pages
- [ ] Hover states work on all icon buttons
