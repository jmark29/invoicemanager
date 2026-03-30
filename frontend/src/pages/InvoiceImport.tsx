import { useState, useCallback, useRef, type DragEvent } from 'react'
import { Link } from 'react-router-dom'
import { Upload, Check, FileText } from 'lucide-react'
import { useClients, useImportParse, useImportConfirm } from '@/hooks/useApi'
import { formatEur } from '@/utils/format'
import type { ImportParsedInvoice, ImportConfirmRequest, ImportConfirmInvoice, ImportConfirmLineItem } from '@/types/api'
import { PageHeader } from '@/components/PageHeader'

type Step = 'upload' | 'review' | 'success'

interface EditableLineItem {
  position: number
  description: string
  amount: string
  match_confidence: string
  linked_provider_invoice_ids: number[]
  linked_amounts: number[]
}

interface EditableInvoice {
  filename: string
  stored_path: string
  invoice_number: string
  invoice_date: string
  period_start: string
  period_end: string
  client_id: string
  status: string
  line_items: EditableLineItem[]
  confidence: string
}

function toEditable(parsed: ImportParsedInvoice): EditableInvoice {
  return {
    filename: parsed.filename,
    stored_path: parsed.stored_path,
    invoice_number: parsed.invoice_number ?? '',
    invoice_date: parsed.invoice_date ?? '',
    period_start: parsed.period_start ?? '',
    period_end: parsed.period_end ?? '',
    client_id: '',
    status: 'sent',
    line_items: parsed.line_items.map((li) => ({
      position: li.position,
      description: li.description,
      amount: String(li.amount),
      match_confidence: li.match_confidence,
      linked_provider_invoice_ids: li.linked_provider_invoice_ids,
      linked_amounts: li.linked_amounts,
    })),
    confidence: parsed.confidence,
  }
}

function calcTotals(items: EditableLineItem[]) {
  const net = items.reduce((sum, li) => sum + (parseFloat(li.amount) || 0), 0)
  const vat = Math.round(net * 0.19 * 100) / 100
  const gross = Math.round((net + vat) * 100) / 100
  return { net, vat, gross }
}

const CONFIDENCE_STYLES: Record<string, string> = {
  high: 'bg-green-100 text-green-700',
  medium: 'bg-yellow-100 text-yellow-700',
  low: 'bg-red-100 text-red-700',
}

const MATCH_DOT: Record<string, string> = {
  high: 'bg-green-500',
  medium: 'bg-yellow-500',
  none: 'bg-gray-300',
}

export function InvoiceImport() {
  const [step, setStep] = useState<Step>('upload')
  const [dragOver, setDragOver] = useState(false)
  const [invoices, setInvoices] = useState<EditableInvoice[]>([])
  const [result, setResult] = useState<{ created: number; linked: number } | null>(null)
  const [error, setError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const { data: clients } = useClients(true)
  const parseMutation = useImportParse()
  const confirmMutation = useImportConfirm()

  const handleFiles = useCallback((files: FileList | File[]) => {
    const accepted = Array.from(files).filter((f) =>
      f.name.endsWith('.docx') || f.name.endsWith('.pdf')
    )
    if (accepted.length === 0) return
    setError(null)
    parseMutation.mutate(accepted, {
      onSuccess: (data) => {
        setInvoices(data.invoices.map(toEditable))
        setStep('review')
      },
      onError: (err) => {
        setError(err instanceof Error ? err.message : 'Parsing fehlgeschlagen')
      },
    })
  }, [parseMutation])

  const handleDrop = (e: DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    handleFiles(e.dataTransfer.files)
  }

  const updateInvoice = (idx: number, field: keyof EditableInvoice, value: string) => {
    setInvoices((prev) => {
      const next = [...prev]
      next[idx] = { ...next[idx], [field]: value } as EditableInvoice
      return next
    })
  }

  const updateLineItem = (invIdx: number, liIdx: number, field: keyof EditableLineItem, value: string) => {
    setInvoices((prev) => {
      const next = [...prev]
      const inv = { ...next[invIdx]! }
      const items = [...inv.line_items]
      items[liIdx] = { ...items[liIdx]!, [field]: value }
      inv.line_items = items
      next[invIdx] = inv
      return next
    })
  }

  const handleConfirm = () => {
    const confirmInvoices: ImportConfirmInvoice[] = invoices
      .filter((inv) => inv.invoice_number && inv.client_id)
      .map((inv) => {
        const { net, vat, gross } = calcTotals(inv.line_items)
        const lineItems: ImportConfirmLineItem[] = inv.line_items.map((li) => ({
          position: li.position,
          description: li.description,
          amount: parseFloat(li.amount) || 0,
          provider_invoice_ids: li.linked_provider_invoice_ids,
          provider_invoice_amounts: li.linked_amounts,
        }))
        return {
          stored_path: inv.stored_path,
          invoice_number: inv.invoice_number,
          invoice_date: inv.invoice_date,
          period_start: inv.period_start || null,
          period_end: inv.period_end || null,
          client_id: inv.client_id,
          status: inv.status,
          line_items: lineItems,
          net_total: net,
          tax_rate: 0.19,
          vat_amount: vat,
          gross_total: gross,
        }
      })

    if (confirmInvoices.length === 0) return

    const request: ImportConfirmRequest = { invoices: confirmInvoices }
    setError(null)
    confirmMutation.mutate(request, {
      onSuccess: (data) => {
        setResult({ created: data.created, linked: data.linked_sources })
        setStep('success')
      },
      onError: (err) => {
        setError(err instanceof Error ? err.message : 'Import fehlgeschlagen')
      },
    })
  }

  return (
    <div>
      <PageHeader title="Rechnungen importieren" />

      {error && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Step 1: Upload */}
      {step === 'upload' && (
        <div className="rounded-lg border border-gray-200 bg-white p-5">
          <h2 className="mb-4 text-sm font-semibold text-gray-700">
            1. Dateien hochladen
          </h2>
          <div
            className={`rounded-lg border-2 border-dashed p-10 text-center transition-colors ${
              dragOver ? 'border-blue-400 bg-blue-50' : 'border-gray-300 bg-gray-50'
            } ${parseMutation.isPending ? 'cursor-wait opacity-60' : 'cursor-pointer'}`}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            onClick={() => !parseMutation.isPending && inputRef.current?.click()}
          >
            <input
              ref={inputRef}
              type="file"
              accept=".docx,.pdf"
              multiple
              title="DOCX/PDF-Dateien auswaehlen"
              className="hidden"
              onChange={(e) => {
                if (e.target.files) handleFiles(e.target.files)
                e.target.value = ''
              }}
              disabled={parseMutation.isPending}
            />
            {parseMutation.isPending ? (
              <div className="flex flex-col items-center gap-2">
                <Upload className="h-8 w-8 animate-pulse text-blue-400" />
                <p className="text-sm text-gray-500">Dateien werden analysiert...</p>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-2">
                <Upload className="h-8 w-8 text-gray-400" />
                <p className="text-sm font-medium text-gray-600">
                  Bestehende Rechnungen importieren (DOCX/PDF)
                </p>
                <p className="text-xs text-gray-400">
                  Dateien hierher ziehen oder klicken zum Auswaehlen
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Step 2: Review */}
      {step === 'review' && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-gray-700">
              2. Rechnungen pruefen ({invoices.length})
            </h2>
            <div className="flex gap-2">
              <button
                onClick={handleConfirm}
                disabled={confirmMutation.isPending || invoices.every((inv) => !inv.invoice_number || !inv.client_id)}
                className="rounded-md bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
              >
                {confirmMutation.isPending ? 'Wird importiert...' : 'Import bestaetigen'}
              </button>
              <button
                onClick={() => { setStep('upload'); setInvoices([]); setError(null) }}
                className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Abbrechen
              </button>
            </div>
          </div>

          {invoices.map((inv, invIdx) => {
            const { net, vat, gross } = calcTotals(inv.line_items)
            return (
              <div key={inv.filename} className="rounded-lg border border-gray-200 bg-white p-5">
                {/* Header with filename and confidence */}
                <div className="mb-4 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <FileText className="h-4 w-4 text-gray-400" />
                    <span className="text-sm font-medium text-gray-700">{inv.filename}</span>
                  </div>
                  <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                    CONFIDENCE_STYLES[inv.confidence] ?? 'bg-gray-100 text-gray-500'
                  }`}>
                    {inv.confidence}
                  </span>
                </div>

                {/* Invoice metadata fields */}
                <div className="mb-4 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
                  <div>
                    <label className="block text-xs font-medium text-gray-600">Rechnungsnummer</label>
                    <input
                      type="text"
                      value={inv.invoice_number}
                      onChange={(e) => updateInvoice(invIdx, 'invoice_number', e.target.value)}
                      className="mt-1 w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm"
                      placeholder="202501-02"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-600">Datum</label>
                    <input
                      type="date"
                      value={inv.invoice_date}
                      onChange={(e) => updateInvoice(invIdx, 'invoice_date', e.target.value)}
                      className="mt-1 w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-600">Zeitraum von</label>
                    <input
                      type="date"
                      value={inv.period_start}
                      onChange={(e) => updateInvoice(invIdx, 'period_start', e.target.value)}
                      className="mt-1 w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-600">Zeitraum bis</label>
                    <input
                      type="date"
                      value={inv.period_end}
                      onChange={(e) => updateInvoice(invIdx, 'period_end', e.target.value)}
                      className="mt-1 w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-600">Kunde</label>
                    <select
                      value={inv.client_id}
                      onChange={(e) => updateInvoice(invIdx, 'client_id', e.target.value)}
                      className="mt-1 w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm"
                    >
                      <option value="">-- Kunde waehlen --</option>
                      {clients?.map((c) => (
                        <option key={c.id} value={c.id}>{c.name}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-600">Status</label>
                    <select
                      value={inv.status}
                      onChange={(e) => updateInvoice(invIdx, 'status', e.target.value)}
                      className="mt-1 w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm"
                    >
                      <option value="draft">Entwurf</option>
                      <option value="sent">Versendet</option>
                      <option value="paid">Bezahlt</option>
                    </select>
                  </div>
                </div>

                {/* Line items table */}
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-200 text-left">
                      <th className="w-16 px-3 py-2 font-medium text-gray-600">Pos</th>
                      <th className="px-3 py-2 font-medium text-gray-600">Bezeichnung</th>
                      <th className="w-40 px-3 py-2 text-right font-medium text-gray-600">Betrag</th>
                      <th className="w-12 px-3 py-2 text-center font-medium text-gray-600">Match</th>
                    </tr>
                  </thead>
                  <tbody>
                    {inv.line_items.map((li, liIdx) => (
                      <tr key={li.position} className="border-b border-gray-100">
                        <td className="px-3 py-2">
                          <input
                            type="number"
                            value={li.position}
                            onChange={(e) => updateLineItem(invIdx, liIdx, 'position', e.target.value)}
                            className="w-full rounded border border-gray-300 px-2 py-1 text-sm"
                          />
                        </td>
                        <td className="px-3 py-2">
                          <input
                            type="text"
                            value={li.description}
                            onChange={(e) => updateLineItem(invIdx, liIdx, 'description', e.target.value)}
                            className="w-full rounded border border-gray-300 px-2 py-1 text-sm"
                          />
                        </td>
                        <td className="px-3 py-2">
                          <input
                            type="number"
                            step="0.01"
                            value={li.amount}
                            onChange={(e) => updateLineItem(invIdx, liIdx, 'amount', e.target.value)}
                            className="w-full rounded border border-gray-300 px-2 py-1 text-right text-sm"
                          />
                        </td>
                        <td className="px-3 py-2 text-center">
                          <span
                            className={`inline-block h-3 w-3 rounded-full ${
                              MATCH_DOT[li.match_confidence] ?? MATCH_DOT.none
                            }`}
                            title={li.match_confidence}
                          />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>

                {/* Totals */}
                <div className="mt-4 flex justify-end">
                  <div className="w-72 space-y-1 text-sm">
                    <div className="flex justify-between border-t border-gray-200 pt-2">
                      <span className="text-gray-600">Netto</span>
                      <span className="font-medium">{formatEur(net)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">USt. 19%</span>
                      <span>{formatEur(vat)}</span>
                    </div>
                    <div className="flex justify-between border-t border-gray-300 pt-2 font-bold">
                      <span>Brutto</span>
                      <span>{formatEur(gross)}</span>
                    </div>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Step 3: Success */}
      {step === 'success' && result && (
        <div className="rounded-lg border border-green-200 bg-green-50 p-5">
          <div className="flex items-center gap-2">
            <Check className="h-5 w-5 text-green-600" />
            <h2 className="text-lg font-semibold text-green-800">Import abgeschlossen</h2>
          </div>
          <p className="mt-2 text-sm text-green-700">
            {result.created} Rechnungen importiert, {result.linked} Quellverknuepfungen erstellt
          </p>
          <div className="mt-4 flex gap-3">
            <Link
              to="/invoices"
              className="rounded-md bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700"
            >
              Zur Rechnungsliste
            </Link>
            <button
              onClick={() => { setStep('upload'); setInvoices([]); setResult(null); setError(null) }}
              className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Weitere importieren
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
