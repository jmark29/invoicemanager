import { useState, useRef, type DragEvent } from 'react'
import { useBulkUpload, useBulkConfirm, useCostCategories } from '@/hooks/useApi'
import type { BulkUploadExtraction, BulkUploadConfirmItem } from '@/types/api'

interface Props {
  categoryId?: string
}

interface ReviewRow extends BulkUploadExtraction {
  // Editable fields for the review table
  editInvoiceNumber: string
  editInvoiceDate: string
  editAmount: string
  editCurrency: string
  editCategoryId: string
  editAssignedMonth: string
  include: boolean
}

function toReviewRow(ext: BulkUploadExtraction, presetCategoryId?: string): ReviewRow {
  return {
    filename: ext.filename,
    stored_path: ext.stored_path,
    invoice_number: ext.invoice_number,
    invoice_date: ext.invoice_date,
    amount: ext.amount,
    currency: ext.currency,
    category_id: ext.category_id,
    confidence: ext.confidence,
    editInvoiceNumber: ext.invoice_number ?? '',
    editInvoiceDate: ext.invoice_date ?? '',
    editAmount: ext.amount != null ? String(ext.amount) : '',
    editCurrency: ext.currency ?? 'EUR',
    editCategoryId: presetCategoryId ?? ext.category_id ?? '',
    editAssignedMonth: '',
    include: true,
  }
}

export function BulkUploadZone({ categoryId }: Props) {
  const [dragOver, setDragOver] = useState(false)
  const [reviewRows, setReviewRows] = useState<ReviewRow[] | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const uploadMutation = useBulkUpload()
  const confirmMutation = useBulkConfirm()
  const { data: categories } = useCostCategories()

  const handleFiles = (files: FileList | File[]) => {
    const pdfFiles = Array.from(files).filter((f) => f.type === 'application/pdf' || f.name.endsWith('.pdf'))
    if (pdfFiles.length === 0) return
    uploadMutation.mutate(
      { files: pdfFiles, categoryId },
      {
        onSuccess: (data) => {
          setReviewRows(data.extractions.map((ext) => toReviewRow(ext, categoryId)))
        },
      },
    )
  }

  const handleDrop = (e: DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    handleFiles(e.dataTransfer.files)
  }

  const updateRow = (idx: number, field: keyof ReviewRow, value: string | boolean) => {
    setReviewRows((prev) => {
      if (!prev) return prev
      const next = [...prev]
      next[idx] = { ...next[idx], [field]: value } as ReviewRow
      return next
    })
  }

  const handleConfirm = () => {
    if (!reviewRows) return
    const items: BulkUploadConfirmItem[] = reviewRows
      .filter((r) => r.include && r.editInvoiceNumber && r.editAmount && r.editCategoryId)
      .map((r) => ({
        filename: r.filename,
        stored_path: r.stored_path,
        invoice_number: r.editInvoiceNumber,
        invoice_date: r.editInvoiceDate,
        amount: parseFloat(r.editAmount),
        currency: r.editCurrency,
        category_id: r.editCategoryId,
        assigned_month: r.editAssignedMonth || null,
      }))

    if (items.length === 0) return
    confirmMutation.mutate(items, {
      onSuccess: () => setReviewRows(null),
    })
  }

  const validCount = reviewRows?.filter(
    (r) => r.include && r.editInvoiceNumber && r.editAmount && r.editCategoryId
  ).length ?? 0

  // Upload zone (no review table yet)
  if (!reviewRows) {
    return (
      <div className="mb-6">
        <div
          className={`rounded-lg border-2 border-dashed p-6 text-center transition-colors ${
            dragOver ? 'border-blue-400 bg-blue-50' : 'border-gray-300 bg-gray-50'
          } ${uploadMutation.isPending ? 'cursor-wait opacity-60' : 'cursor-pointer'}`}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => !uploadMutation.isPending && inputRef.current?.click()}
        >
          <input
            ref={inputRef}
            type="file"
            accept=".pdf"
            multiple
            title="PDF-Dateien auswählen"
            className="hidden"
            onChange={(e) => {
              if (e.target.files) handleFiles(e.target.files)
              e.target.value = ''
            }}
            disabled={uploadMutation.isPending}
          />
          {uploadMutation.isPending ? (
            <p className="text-sm text-gray-500">PDFs werden verarbeitet...</p>
          ) : (
            <p className="text-sm text-gray-500">
              PDF-Rechnungen hierher ziehen oder klicken zum Auswählen (Mehrfachauswahl)
            </p>
          )}
        </div>
        {uploadMutation.isError && (
          <p className="mt-2 text-sm text-red-600">Fehler: {uploadMutation.error.message}</p>
        )}
      </div>
    )
  }

  // Review table
  return (
    <div className="mb-6 rounded-lg border border-blue-200 bg-blue-50 p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-700">
          Hochgeladene Rechnungen prüfen ({reviewRows.length})
        </h3>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={handleConfirm}
            disabled={confirmMutation.isPending || validCount === 0}
            className="rounded-md bg-blue-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {confirmMutation.isPending ? 'Wird erstellt...' : `${validCount} Übernehmen`}
          </button>
          <button
            type="button"
            onClick={() => setReviewRows(null)}
            className="rounded-md border border-gray-300 bg-white px-4 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Abbrechen
          </button>
        </div>
      </div>

      {confirmMutation.isError && (
        <p className="mb-3 text-sm text-red-600">Fehler: {confirmMutation.error.message}</p>
      )}
      {confirmMutation.isSuccess && confirmMutation.data && (
        <p className="mb-3 text-sm text-green-700">
          {confirmMutation.data.created} erstellt, {confirmMutation.data.auto_matched} automatisch zugeordnet.
          {confirmMutation.data.errors.length > 0 && ` ${confirmMutation.data.errors.length} Fehler.`}
        </p>
      )}

      <div className="overflow-x-auto rounded-lg border border-gray-200">
        <table className="min-w-full divide-y divide-gray-200 bg-white text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="w-8 px-2 py-2"><span className="sr-only">Auswahl</span></th>
              <th className="px-3 py-2 text-left font-medium text-gray-600">Datei</th>
              <th className="px-3 py-2 text-left font-medium text-gray-600">Rechnungsnr.</th>
              <th className="px-3 py-2 text-left font-medium text-gray-600">Datum</th>
              <th className="px-3 py-2 text-right font-medium text-gray-600">Betrag</th>
              <th className="px-3 py-2 text-left font-medium text-gray-600">Währung</th>
              <th className="px-3 py-2 text-left font-medium text-gray-600">Kategorie</th>
              <th className="px-3 py-2 text-left font-medium text-gray-600">Monat</th>
              <th className="px-3 py-2 text-center font-medium text-gray-600">Konfidenz</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {reviewRows.map((row, idx) => (
              <tr key={row.filename} className={row.include ? '' : 'opacity-40'}>
                <td className="px-2 py-2 text-center">
                  <input
                    type="checkbox"
                    title="Einschließen"
                    checked={row.include}
                    onChange={(e) => updateRow(idx, 'include', e.target.checked)}
                    className="h-4 w-4 rounded border-gray-300"
                  />
                </td>
                <td className="px-3 py-2 text-xs text-gray-600 max-w-[120px] truncate" title={row.filename}>
                  {row.filename}
                </td>
                <td className="px-3 py-2">
                  <input
                    type="text"
                    value={row.editInvoiceNumber}
                    onChange={(e) => updateRow(idx, 'editInvoiceNumber', e.target.value)}
                    className="w-full rounded border border-gray-300 px-2 py-1 text-xs"
                    placeholder="Rechnungsnr."
                  />
                </td>
                <td className="px-3 py-2">
                  <input
                    type="date"
                    title="Rechnungsdatum"
                    value={row.editInvoiceDate}
                    onChange={(e) => updateRow(idx, 'editInvoiceDate', e.target.value)}
                    className="w-full rounded border border-gray-300 px-2 py-1 text-xs"
                  />
                </td>
                <td className="px-3 py-2">
                  <input
                    type="number"
                    step="0.01"
                    value={row.editAmount}
                    onChange={(e) => updateRow(idx, 'editAmount', e.target.value)}
                    className="w-24 rounded border border-gray-300 px-2 py-1 text-xs text-right"
                    placeholder="0.00"
                  />
                </td>
                <td className="px-3 py-2">
                  <select
                    value={row.editCurrency}
                    onChange={(e) => updateRow(idx, 'editCurrency', e.target.value)}
                    className="rounded border border-gray-300 px-2 py-1 text-xs"
                    aria-label="Währung"
                  >
                    <option value="EUR">EUR</option>
                    <option value="USD">USD</option>
                  </select>
                </td>
                <td className="px-3 py-2">
                  {categoryId ? (
                    <span className="text-xs text-gray-600">{categoryId}</span>
                  ) : (
                    <select
                      value={row.editCategoryId}
                      onChange={(e) => updateRow(idx, 'editCategoryId', e.target.value)}
                      className="w-full rounded border border-gray-300 px-2 py-1 text-xs"
                      aria-label="Kategorie"
                    >
                      <option value="">--</option>
                      {categories?.map((c) => (
                        <option key={c.id} value={c.id}>{c.name}</option>
                      ))}
                    </select>
                  )}
                </td>
                <td className="px-3 py-2">
                  <input
                    type="month"
                    title="Zugeordneter Monat"
                    value={row.editAssignedMonth}
                    onChange={(e) => updateRow(idx, 'editAssignedMonth', e.target.value)}
                    className="w-full rounded border border-gray-300 px-2 py-1 text-xs"
                  />
                </td>
                <td className="px-3 py-2 text-center">
                  <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                    row.confidence === 'high' ? 'bg-green-100 text-green-700' :
                    row.confidence === 'medium' ? 'bg-yellow-100 text-yellow-700' :
                    'bg-gray-100 text-gray-500'
                  }`}>
                    {row.confidence}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
