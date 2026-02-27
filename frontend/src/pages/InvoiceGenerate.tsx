import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { MonthSelector } from '@/components/MonthSelector'
import { AmountDisplay } from '@/components/AmountDisplay'
import { PageHeader } from '@/components/PageHeader'
import { useClients, useInvoicePreview, useGenerateInvoice } from '@/hooks/useApi'
import { invoiceNumber, todayISO, formatEur } from '@/utils/format'
import type { InvoicePreviewResponse } from '@/types/api'

export function InvoiceGenerate() {
  const navigate = useNavigate()
  const now = new Date()
  const [year, setYear] = useState(now.getFullYear())
  const [month, setMonth] = useState(now.getMonth() + 1)
  const [clientId, setClientId] = useState('')
  const [preview, setPreview] = useState<InvoicePreviewResponse | null>(null)
  const [overrides, setOverrides] = useState<Record<number, number>>({})
  const [invNumber, setInvNumber] = useState('')
  const [invDate, setInvDate] = useState(todayISO())
  const [notes, setNotes] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [generated, setGenerated] = useState<{ id: number; filename: string } | null>(null)

  const { data: clients } = useClients(true)
  const previewMutation = useInvoicePreview()
  const generateMutation = useGenerateInvoice()

  // Auto-select first client
  if (clients && clients.length > 0 && !clientId) {
    setClientId(clients[0]!.id)
  }

  const selectedClient = clients?.find((c) => c.id === clientId)

  const handlePreview = async () => {
    if (!clientId) return
    setError(null)
    setGenerated(null)
    setOverrides({})
    try {
      const result = await previewMutation.mutateAsync({ client_id: clientId, year, month })
      setPreview(result)
      if (selectedClient) {
        setInvNumber(invoiceNumber(year, month, selectedClient.client_number))
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Vorschau fehlgeschlagen')
    }
  }

  const handleOverride = (position: number, value: string) => {
    const num = parseFloat(value)
    if (isNaN(num)) {
      const next = { ...overrides }
      delete next[position]
      setOverrides(next)
    } else {
      setOverrides({ ...overrides, [position]: num })
    }
  }

  // Recalculate totals with overrides
  const effectiveItems = preview?.items.map((item) => ({
    ...item,
    amount: overrides[item.position] ?? item.amount,
  })) ?? []

  const netTotal = effectiveItems.reduce((sum, item) => sum + item.amount, 0)
  const vatRate = selectedClient?.vat_rate ?? 0.19
  const vatAmount = Math.round(netTotal * vatRate * 100) / 100
  const grossTotal = Math.round((netTotal + vatAmount) * 100) / 100

  const handleGenerate = async () => {
    if (!clientId || !preview) return
    setError(null)
    try {
      const hasOverrides = Object.keys(overrides).length > 0
      const result = await generateMutation.mutateAsync({
        client_id: clientId,
        year,
        month,
        invoice_number: invNumber,
        invoice_date: invDate,
        overrides: hasOverrides ? overrides : undefined,
        notes: notes || undefined,
      })
      setGenerated({ id: result.id, filename: result.filename ?? invNumber })
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Generierung fehlgeschlagen')
    }
  }

  return (
    <div>
      <PageHeader title="Rechnung erstellen" />

      {/* Step 1: Select month + client */}
      <div className="rounded-lg border border-gray-200 bg-white p-5">
        <h2 className="mb-4 text-sm font-semibold text-gray-700">1. Monat und Kunde</h2>
        <div className="flex flex-wrap items-end gap-4">
          <MonthSelector
            year={year}
            month={month}
            onChange={(y, m) => { setYear(y); setMonth(m); setPreview(null); setGenerated(null) }}
          />
          <div>
            <label className="block text-xs font-medium text-gray-600">Kunde</label>
            <select
              value={clientId}
              onChange={(e) => { setClientId(e.target.value); setPreview(null); setGenerated(null) }}
              className="mt-1 rounded-md border border-gray-300 px-3 py-1.5 text-sm"
            >
              <option value="">-- Kunde w\u00E4hlen --</option>
              {clients?.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>
          <button
            onClick={() => void handlePreview()}
            disabled={!clientId || previewMutation.isPending}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {previewMutation.isPending ? 'Laden...' : 'Vorschau'}
          </button>
        </div>
      </div>

      {error && (
        <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Step 2: Preview with editable amounts */}
      {preview && !generated && (
        <div className="mt-6 rounded-lg border border-gray-200 bg-white p-5">
          <h2 className="mb-4 text-sm font-semibold text-gray-700">2. Positionen pr\u00FCfen</h2>

          {preview.warnings.length > 0 && (
            <div className="mb-4 rounded-md bg-yellow-50 p-3 text-sm text-yellow-800">
              {preview.warnings.map((w, i) => <p key={i}>{w}</p>)}
            </div>
          )}

          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 text-left">
                <th className="w-12 px-3 py-2 font-medium text-gray-600">Pos</th>
                <th className="px-3 py-2 font-medium text-gray-600">Bezeichnung</th>
                <th className="w-20 px-3 py-2 font-medium text-gray-600">Typ</th>
                <th className="w-40 px-3 py-2 text-right font-medium text-gray-600">Betrag (auto)</th>
                <th className="w-40 px-3 py-2 text-right font-medium text-gray-600">Betrag (\u00FCberschreiben)</th>
              </tr>
            </thead>
            <tbody>
              {preview.items.map((item) => (
                <tr key={item.position} className="border-b border-gray-100">
                  <td className="px-3 py-2 text-gray-500">{item.position}</td>
                  <td className="px-3 py-2">
                    {item.label}
                    {item.warnings.length > 0 && (
                      <span className="ml-2 text-xs text-yellow-600" title={item.warnings.join(', ')}>
                        \u26A0
                      </span>
                    )}
                  </td>
                  <td className="px-3 py-2 text-xs text-gray-500">{item.source_type}</td>
                  <td className="px-3 py-2 text-right text-gray-600">
                    {formatEur(item.amount)}
                  </td>
                  <td className="px-3 py-2 text-right">
                    <input
                      type="number"
                      step="0.01"
                      placeholder={item.amount.toFixed(2)}
                      value={overrides[item.position] ?? ''}
                      onChange={(e) => handleOverride(item.position, e.target.value)}
                      className="w-full rounded border border-gray-300 px-2 py-1 text-right text-sm"
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {/* Totals */}
          <div className="mt-4 flex justify-end">
            <div className="w-80 space-y-1 text-sm">
              <div className="flex justify-between border-t border-gray-200 pt-2">
                <span className="text-gray-600">Netto-Rechnungsbetrag</span>
                <AmountDisplay amount={netTotal} className="font-medium" />
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Umsatzsteuer {Math.round(vatRate * 100)}%</span>
                <AmountDisplay amount={vatAmount} />
              </div>
              <div className="flex justify-between border-t border-gray-300 pt-2 font-bold">
                <span>Brutto-Rechnungsbetrag</span>
                <AmountDisplay amount={grossTotal} className="font-bold" />
              </div>
            </div>
          </div>

          {/* Step 3: Invoice number + date */}
          <div className="mt-6 border-t border-gray-200 pt-4">
            <h2 className="mb-3 text-sm font-semibold text-gray-700">3. Rechnungsdaten</h2>
            <div className="flex flex-wrap gap-4">
              <div>
                <label className="block text-xs font-medium text-gray-600">Rechnungsnummer</label>
                <input
                  type="text"
                  value={invNumber}
                  onChange={(e) => setInvNumber(e.target.value)}
                  className="mt-1 rounded-md border border-gray-300 px-3 py-1.5 text-sm"
                  placeholder="202501-02"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600">Rechnungsdatum</label>
                <input
                  type="date"
                  value={invDate}
                  onChange={(e) => setInvDate(e.target.value)}
                  className="mt-1 rounded-md border border-gray-300 px-3 py-1.5 text-sm"
                />
              </div>
              <div className="flex-1">
                <label className="block text-xs font-medium text-gray-600">Notizen (optional)</label>
                <input
                  type="text"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  className="mt-1 w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm"
                />
              </div>
            </div>
            <div className="mt-4">
              <button
                onClick={() => void handleGenerate()}
                disabled={!invNumber || generateMutation.isPending}
                className="rounded-md bg-green-600 px-6 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
              >
                {generateMutation.isPending ? 'Generiere...' : 'Rechnung generieren'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Step 4: Success */}
      {generated && (
        <div className="mt-6 rounded-lg border border-green-200 bg-green-50 p-5">
          <h2 className="text-lg font-semibold text-green-800">Rechnung erstellt!</h2>
          <p className="mt-1 text-sm text-green-700">
            {generated.filename} wurde erfolgreich generiert.
          </p>
          <div className="mt-4 flex gap-3">
            <a
              href={`/api/invoices/${generated.id}/download`}
              target="_blank"
              rel="noopener noreferrer"
              className="rounded-md bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700"
            >
              PDF herunterladen
            </a>
            <button
              onClick={() => navigate(`/invoices/${generated.id}`)}
              className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Details anzeigen
            </button>
            <button
              onClick={() => { setPreview(null); setGenerated(null); setOverrides({}) }}
              className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Weitere Rechnung
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
