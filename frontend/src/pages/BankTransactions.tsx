import { useState } from 'react'
import { PageHeader } from '@/components/PageHeader'
import { FileUpload } from '@/components/FileUpload'
import { AmountDisplay } from '@/components/AmountDisplay'
import { ErrorAlert } from '@/components/ErrorAlert'
import { useBankTransactions, useCostCategories, useImportBankXlsx, useUpdateBankTransaction } from '@/hooks/useApi'
import { formatDateGerman } from '@/utils/format'
import type { BankImportResponse } from '@/types/api'

export function BankTransactions() {
  const [categoryFilter, setCategoryFilter] = useState<string | undefined>(undefined)
  const [importResult, setImportResult] = useState<BankImportResponse | null>(null)

  const { data: transactions, isLoading, isError, error, refetch } = useBankTransactions({
    category_id: categoryFilter,
  })
  const { data: categories } = useCostCategories()
  const importMutation = useImportBankXlsx()
  const updateMutation = useUpdateBankTransaction()

  const handleImport = async (file: File) => {
    try {
      const result = await importMutation.mutateAsync(file)
      setImportResult(result)
    } catch {
      setImportResult(null)
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
        {importResult && (
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

      {/* Filter */}
      <div className="mb-4">
        <select
          value={categoryFilter ?? ''}
          onChange={(e) => setCategoryFilter(e.target.value || undefined)}
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
