import { useState } from 'react'
import { PageHeader } from '@/components/PageHeader'
import { AmountDisplay } from '@/components/AmountDisplay'
import { ErrorAlert } from '@/components/ErrorAlert'
import { useProviderInvoices, useCostCategories } from '@/hooks/useApi'
import { formatDateGerman } from '@/utils/format'

export function ProviderInvoices() {
  const [categoryFilter, setCategoryFilter] = useState<string | undefined>(undefined)
  const [monthFilter, setMonthFilter] = useState<string | undefined>(undefined)

  const { data: invoices, isLoading, isError, error, refetch } = useProviderInvoices({
    category_id: categoryFilter,
    assigned_month: monthFilter,
  })
  const { data: categories } = useCostCategories()

  return (
    <div>
      <PageHeader title="Lieferantenrechnungen" />

      {/* Filters */}
      <div className="mb-4 flex flex-wrap gap-3">
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

        <input
          type="month"
          value={monthFilter ?? ''}
          onChange={(e) => setMonthFilter(e.target.value || undefined)}
          className="rounded-md border border-gray-300 px-3 py-1.5 text-sm"
          placeholder="Zugeordneter Monat"
        />
      </div>

      {isError ? (
        <ErrorAlert error={error} onRetry={() => void refetch()} />
      ) : isLoading ? (
        <p className="text-sm text-gray-500">Laden...</p>
      ) : !invoices || invoices.length === 0 ? (
        <div className="rounded-lg border border-gray-200 bg-white p-8 text-center text-sm text-gray-500">
          Keine Lieferantenrechnungen gefunden.
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-gray-200">
          <table className="min-w-full divide-y divide-gray-200 bg-white text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Nr.</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Kategorie</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Datum</th>
                <th className="px-4 py-3 text-right font-medium text-gray-600">Betrag</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">W\u00E4hrung</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Zugeordnet</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">PDF</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {invoices.map((inv) => (
                <tr key={inv.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium">{inv.invoice_number}</td>
                  <td className="px-4 py-3 text-gray-600">{inv.category_id}</td>
                  <td className="px-4 py-3 text-gray-600">{formatDateGerman(inv.invoice_date)}</td>
                  <td className="px-4 py-3 text-right"><AmountDisplay amount={inv.amount} /></td>
                  <td className="px-4 py-3 text-gray-500">{inv.currency}</td>
                  <td className="px-4 py-3 text-gray-600">{inv.assigned_month ?? '-'}</td>
                  <td className="px-4 py-3">
                    {inv.file_path ? (
                      <a
                        href={`/api/provider-invoices/${inv.id}/download`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs text-blue-600 hover:underline"
                      >
                        Download
                      </a>
                    ) : (
                      <span className="text-xs text-gray-400">-</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
