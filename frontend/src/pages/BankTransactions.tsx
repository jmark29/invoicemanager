import { useRef, useState } from 'react'
import { PageHeader } from '@/components/PageHeader'
import { FileUpload } from '@/components/FileUpload'
import { AmountDisplay } from '@/components/AmountDisplay'
import { ErrorAlert } from '@/components/ErrorAlert'
import { useBankTransactions, useCostCategories, useImportBankXlsx, useUpdateBankTransaction, useBankImportHistory } from '@/hooks/useApi'
import { formatDateGerman } from '@/utils/format'
import type { BankImportResponse } from '@/types/api'

export function BankTransactions() {
  const [categoryFilter, setCategoryFilter] = useState<string | undefined>(undefined)
  const [importResult, setImportResult] = useState<BankImportResponse | null>(null)
  const [showHistory, setShowHistory] = useState(false)
  const [showDupDialog, setShowDupDialog] = useState(false)
  const lastImportFile = useRef<File | null>(null)

  const { data: transactions, isLoading, isError, error, refetch } = useBankTransactions({
    category_id: categoryFilter,
  })
  const { data: categories } = useCostCategories()
  const importMutation = useImportBankXlsx()
  const updateMutation = useUpdateBankTransaction()
  const { data: importHistory } = useBankImportHistory()

  const handleImport = async (file: File, forceImportAll = false) => {
    lastImportFile.current = file
    try {
      const result = await importMutation.mutateAsync({ file, forceImportAll })
      setImportResult(result)
      if (result.skipped_duplicate > 0 && !forceImportAll) {
        setShowDupDialog(true)
      } else {
        setShowDupDialog(false)
      }
    } catch {
      setImportResult(null)
      setShowDupDialog(false)
    }
  }

  const handleForceImport = () => {
    if (lastImportFile.current) {
      setShowDupDialog(false)
      void handleImport(lastImportFile.current, true)
    }
  }

  const handleCategoryChange = (txId: number, categoryId: string) => {
    updateMutation.mutate({
      id: txId,
      data: { category_id: categoryId || null },
    })
  }

  return (
    <div>
      <PageHeader title="Banktransaktionen" />

      {/* Import */}
      <div className="mb-6">
        <h2 className="mb-2 text-sm font-semibold text-gray-700">XLSX Import</h2>
        <FileUpload
          accept=".xlsx,.xls"
          onFile={(f) => void handleImport(f)}
          label="Bank-XLSX hierher ziehen oder klicken"
          disabled={importMutation.isPending}
        />
        {importMutation.isPending && (
          <p className="mt-2 text-sm text-gray-500">Importiere...</p>
        )}
        {importResult && !showDupDialog && (
          <div className="mt-2 rounded-md bg-blue-50 p-3 text-sm text-blue-800">
            Importiert: {importResult.imported} | Duplikate: {importResult.skipped_duplicate} | Auto-zugeordnet: {importResult.auto_matched}
            {importResult.errors.length > 0 && (
              <div className="mt-1 text-red-600">
                {importResult.errors.map((e, i) => <p key={i}>{e}</p>)}
              </div>
            )}
          </div>
        )}
        {importMutation.isError && (
          <p className="mt-2 text-sm text-red-600">
            Import fehlgeschlagen: {importMutation.error.message}
          </p>
        )}
      </div>

      {/* Duplicate Warning Dialog */}
      {showDupDialog && importResult && importResult.potential_duplicates.length > 0 && (
        <div className="mb-6 rounded-lg border border-yellow-300 bg-yellow-50 p-4">
          <h3 className="mb-2 text-sm font-semibold text-yellow-800">
            {importResult.skipped_duplicate} mögliche Duplikate gefunden
          </h3>
          <p className="mb-3 text-sm text-yellow-700">
            {importResult.imported} Transaktionen wurden importiert.
            Die folgenden Transaktionen existieren bereits und wurden übersprungen:
          </p>
          <div className="mb-3 max-h-48 overflow-y-auto rounded border border-yellow-200 bg-white">
            <table className="min-w-full text-sm">
              <thead className="bg-yellow-50">
                <tr>
                  <th className="px-3 py-1.5 text-left font-medium text-yellow-800">Datum</th>
                  <th className="px-3 py-1.5 text-right font-medium text-yellow-800">Betrag</th>
                  <th className="px-3 py-1.5 text-left font-medium text-yellow-800">Beschreibung</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-yellow-100">
                {importResult.potential_duplicates.map((d, i) => (
                  <tr key={i}>
                    <td className="px-3 py-1.5 whitespace-nowrap">{formatDateGerman(d.booking_date)}</td>
                    <td className="px-3 py-1.5 text-right whitespace-nowrap">
                      <AmountDisplay amount={d.amount_eur} />
                    </td>
                    <td className="px-3 py-1.5 max-w-xs truncate" title={d.description}>{d.description}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="flex gap-3">
            <button
              type="button"
              onClick={handleForceImport}
              className="rounded-md bg-yellow-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-yellow-700"
              disabled={importMutation.isPending}
            >
              Trotzdem importieren
            </button>
            <button
              type="button"
              onClick={() => setShowDupDialog(false)}
              className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Duplikate überspringen
            </button>
          </div>
        </div>
      )}

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

      {/* Filter */}
      <div className="mb-4">
        <select
          value={categoryFilter ?? ''}
          onChange={(e) => setCategoryFilter(e.target.value || undefined)}
          title="Kategorie filtern"
          className="rounded-md border border-gray-300 px-3 py-1.5 text-sm"
        >
          <option value="">Alle Kategorien</option>
          {categories?.map((c) => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>
      </div>

      {/* Table */}
      {isError ? (
        <ErrorAlert error={error} onRetry={() => void refetch()} />
      ) : isLoading ? (
        <p className="text-sm text-gray-500">Laden...</p>
      ) : !transactions || transactions.length === 0 ? (
        <div className="rounded-lg border border-gray-200 bg-white p-8 text-center text-sm text-gray-500">
          Keine Banktransaktionen vorhanden. Importieren Sie eine XLSX-Datei.
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-gray-200">
          <table className="min-w-full divide-y divide-gray-200 bg-white text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Buchungstag</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Beschreibung</th>
                <th className="px-4 py-3 text-right font-medium text-gray-600">Betrag</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Kategorie</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Referenz</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {transactions.map((tx) => (
                <tr key={tx.id} className={!tx.category_id ? 'bg-yellow-50' : 'hover:bg-gray-50'}>
                  <td className="px-4 py-3 whitespace-nowrap">{formatDateGerman(tx.booking_date)}</td>
                  <td className="px-4 py-3 max-w-xs truncate" title={tx.description}>{tx.description}</td>
                  <td className="px-4 py-3 text-right whitespace-nowrap">
                    <AmountDisplay amount={tx.amount_eur} />
                  </td>
                  <td className="px-4 py-3">
                    <select
                      value={tx.category_id ?? ''}
                      onChange={(e) => handleCategoryChange(tx.id, e.target.value)}
                      title="Kategorie zuordnen"
                      className="rounded border border-gray-300 px-1.5 py-0.5 text-xs"
                    >
                      <option value="">-- Keine --</option>
                      {categories?.map((c) => (
                        <option key={c.id} value={c.id}>{c.name}</option>
                      ))}
                    </select>
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-500">{tx.reference ?? '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
