# Monatliche Rechnungserstellung - Workflow

## Übersicht

Dieses Tool erstellt monatliche Rechnungen für DRS Holding AG basierend auf:
- **Feste Positionen**: Pos 1 (PM/Konzeption: 16.450 EUR), Pos 2 (Senior FM: 8.300 EUR)
- **Externe Rechnungen**: Pos 3 (Junior FM), Pos 4 (Cloud Engineer), Pos 6 (Mobile/QA)
- **Upwork**: Pos 5 (Mobile Entwickler)

## Dateien

| Datei | Zweck |
|-------|-------|
| `config.json` | Konfiguration: Kunden, Positionen, Regeln |
| `tracking.json` | Tracking: Upwork-Zuordnungen, generierte Rechnungen |
| `generate_invoice.py` | Hauptskript zur Rechnungserstellung |
| `AR202506-02.docx` | Template (letzte Rechnung als Vorlage) |

## Monatlicher Workflow

### Schritt 1: Daten zusammenstellen

Stelle folgende Informationen bereit:

1. **Upwork XLSX** - Aktuelle Transaktionsexport (im Ordner ablegen)
2. **Pos 3 (Junior FM)** - Monatlicher Rechnungsbetrag
3. **Pos 4 (Server/AWS)** - Entweder:
   - Monatsbetrag direkt, ODER
   - Quartalsrechnung + Monate zur Verteilung
4. **Pos 6 (Mobile/QA)** - Rechnungsbetrag (ggf. nach EUR-Umrechnung + Bankgebühren)
5. **Optional**: Reisekosten oder andere Zusatzpositionen

### Schritt 2: Rechnung generieren

```bash
python3 invoice_data/generate_invoice.py \
  --month 2026-01 \
  --client drs \
  --pos3 1800.00 \
  --pos4 2851.20 \
  --pos6 2500.00 \
  --upwork-xlsx upwork-transactions_20260225.xlsx
```

### Schritt 3: Prüfen und PDF erstellen

Die DOCX-Rechnung wird im Hauptordner erstellt. Prüfe die Rechnung und konvertiere bei Bedarf zu PDF.

## Upwork-Tracking

Das Tool trackt automatisch, welche Upwork-Transaktion in welcher Rechnung berücksichtigt wurde:
- **Zuordnung nach Perioden-Ende**: Eine Transaktion "Invoice for Jan 26-Feb 1, 2026" wird Februar zugeordnet (Enddatum Feb 1)
- **Keine Doppelzählung**: Einmal zugeordnete Transaktionen werden übersprungen
- Tracking in `tracking.json` → Feld `upwork_transactions`

## Cloud Engineer Kostenverteilung

Für Quartalsrechnungen nutze die Python-Funktion:

```python
from invoice_data.generate_invoice import distribute_cost_by_working_days
# Verteile 8.553,60 EUR auf Q1/2026
verteilung = distribute_cost_by_working_days(8553.60, [(2026,1),(2026,2),(2026,3)])
# -> {(2026,1): 2851.20, (2026,2): 2715.43, (2026,3): 2986.97}
```

Die Verteilung basiert auf Arbeitstagen (Mo-Fr, abzgl. Hessen-Feiertage).

## Cowork-Nutzung

In einer Cowork-Session kannst du einfach sagen:

> "Erstelle die Rechnung für Januar 2026. Pos 3: 1.800 EUR, Pos 4: 2.851,20 EUR, Pos 6: 2.500 EUR. Upwork-Daten liegen im Ordner."

Claude liest dann die Config, verarbeitet die Upwork-Daten, und generiert die Rechnung.
