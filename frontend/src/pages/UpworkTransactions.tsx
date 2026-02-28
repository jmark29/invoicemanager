import { useState } from 'react'
import { PageHeader } from '@/components/PageHeader'
import { FileUpload } from '@/components/FileUpload'
import { AmountDisplay } from '@/components/AmountDisplay'
import { ErrorAlert } from '@/components/ErrorAlert'
import { useUpworkTransactions, useCostCategories, useImportUpworkXlsx, useUpworkImportHistory } from '@/hooks/useApi'
import { formatDateGerman } from '@/utils/format'
import type { UpworkImportResponse } from '@/types/api'

export function UpworkTransactions() {
  const [monthFilter, setMonthFilter] = useState<string | undefined>(undefined)
  const [importCategoryId, setImportCategoryId] = useState<string | undefined>(undefined)
  const [importResult, setImportResult] = useState<UpworkImportResponse | null>(null)
  const [showHistory, setShowHistory] = useState(false)

  const { data: transactions, isLoading, isError, error, refetch } = useUpworkTransactions({
    assigned_month: monthFilter,
  })
  const { data: categories } = useCostCategories()
  const importMutation = useImportUpworkXlsx()
  const { data: importHistory } = useUpworkImportHistory()

  const handleImport = async (file: File) => {
    try {
      const result = await importMutation.mutateAsync({ file, categoryId: importCategoryId })
      setImportResult(result)
    } catch {
      setImportResult(null)
    }
  }

  // Group by month for summary
  const monthTotals = (transactions ?? []).reduce<Record<string, number>>((acc, tx) => {
    const key = tx.assigned_month ?? 'Nicht zugeordnet'
    acc[key] = (acc[key] ?? 0) + tx.amount_eur
    return acc
  }, {})

  return (
    <div>
      <PageHeader title="Upwork-Transaktionen" />

      {/* Import */}
      <div className="mb-6">
        <h2 className="mb-2 text-sm font-semibold text-gray-700">XLSX Import</h2>
        <div className="mb-2">
          <label className="text-xs font-medium text-gray-600">Kategorie für Import (optional)</label>
          <select
            value={importCategoryId ?? ''}
            onChange={(e) => setImportCategoryId(e.target.value || undefined)}
            className="ml-2 rounded-md border border-gray-300 px-2 py-1 text-sm"
          >
            <option value="">Keine</option>
            {categories?.filter((c) => c.cost_type === 'upwork').map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
        </div>
        <FileUpload
          accept=".xlsx,.xls"
          onFile={(f) => void handleImport(f)}
          label="Upwork-XLSX hierher ziehen oder klicken"
          disabled={importMutation.isPending}
        />
        {importMutation.isPending && <p className="mt-2 text-sm text-gray-500">Importiere...</p>}
        {importResult && (
          <div className="mt-2 rounded-md bg-blue-50 p-3 text-sm text-blue-800">
            Importiert: {importResult.imported} | Duplikate: {importResult.skipped_duplicate} | Ohne Betrag: {importResult.skipped_no_amount} | Ohne Periode: {importResult.skipped_no_period}
            {importResult.errors.length > 0 && (
              <div className="mt-1 text-red-600">
                {importResult.errors.map((e, i) => <p key={i}>{e}</p>)}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Import History */}
      {importHistory && importHistory.length > 0 && (
        <div className="mb-6">
          <button
            type="button"
            onClick={() => setShowHistory(!showHistory)}
            className="text-sm font-semibold text-gray-700 hover:text-blue-600"
          >
            Import-Verlauf ({importHistory.length}) {showHistory ? '▲' : '▼'}
          </button>
          {showHistory && (
            <div className="mt-2 overflow-x-auto rounded-lg border border-gray-200">
              <table className="min-w-full divide-y divide-gray-200 bg-white text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-2 text-left font-medium text-gray-600">Datum</th>
                    <th className="px-4 py-2 text-left font-medium text-gray-600">Datei</th>
                    <th className="px-4 py-2 text-right font-medium text-gray-600">Importiert</th>
                    <th className="px-4 py-2 text-right font-medium text-gray-600">Übersprungen</th>
                    <th className="px-4 py-2 text-left font-medium text-gray-600">Hinweise</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {importHistory.map((h) => (
                    <tr key={h.id} className="hover:bg-gray-50">
                      <td className="px-4 py-2 whitespace-nowrap">
                        {new Date(h.imported_at).toLocaleString('de-DE')}
                      </td>
                      <td className="px-4 py-2">{h.original_filename}</td>
                      <td className="px-4 py-2 text-right">{h.record_count}</td>
                      <td className="px-4 py-2 text-right">{h.skipped_count}</td>
                      <td className="px-4 py-2 text-xs text-gray-500 max-w-xs truncate" title={h.notes ?? ''}>
                        {h.notes ?? '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Month summary */}
      {Object.keys(monthTotals).length > 0 && (
        <div className="mb-6">
          <h2 className="mb-2 text-sm font-semibold text-gray-700">Monatssummen</h2>
          <div className="flex flex-wrap gap-3">
            {Object.entries(monthTotals)
              .sort(([a], [b]) => a.localeCompare(b))
              .map(([month, total]) => (
                <div key={month} className="rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm">
                  <span className="font-medium text-gray-700">{month}:</span>{' '}
                  <AmountDisplay amount={total} />
                </div>
              ))}
          </div>
        </div>
      )}

      {/* Filter */}
      <div className="mb-4">
        <input
          type="month"
          value={monthFilter ?? ''}
          onChange={(e) => setMonthFilter(e.target.value || undefined)}
          className="rounded-md border border-gray-300 px-3 py-1.5 text-sm"
          placeholder="Monat filtern"
        />
      </div>

      {/* Table */}
      {isError ? (
        <ErrorAlert error={error} onRetry={() => void refetch()} />
      ) : isLoading ? (
        <p className="text-sm text-gray-500">Laden...</p>
      ) : !transactions || transactions.length === 0 ? (
        <div className="rounded-lg border border-gray-200 bg-white p-8 text-center text-sm text-gray-500">
          Keine Upwork-Transaktionen vorhanden.
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-gray-200">
          <table className="min-w-full divide-y divide-gray-200 bg-white text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Datum</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">TX-ID</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Beschreibung</th>
                <th className="px-4 py-3 text-right font-medium text-gray-600">Betrag</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Freelancer</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Monat</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {transactions.map((tx) => (
                <tr key={tx.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 whitespace-nowrap">{formatDateGerman(tx.tx_date)}</td>
                  <td className="px-4 py-3 text-xs text-gray-500">{tx.tx_id}</td>
                  <td className="px-4 py-3 max-w-xs truncate">{tx.description ?? '-'}</td>
                  <td className="px-4 py-3 text-right whitespace-nowrap">
                    <AmountDisplay amount={tx.amount_eur} />
                  </td>
                  <td className="px-4 py-3 text-gray-600">{tx.freelancer_name ?? '-'}</td>
                  <td className="px-4 py-3 text-gray-600">{tx.assigned_month ?? '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
