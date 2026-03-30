import { useState } from 'react'
import { ChevronDown, ChevronRight, Check, AlertTriangle, X } from 'lucide-react'
import { useCostReconciliation, useCostReconciliationDetail } from '@/hooks/useApi'
import { formatEur, formatDateGerman } from '@/utils/format'
import { PageHeader } from '@/components/PageHeader'

export function CostReconciliation() {
  const { data, isLoading, isError } = useCostReconciliation()
  const [expandedCategory, setExpandedCategory] = useState<string | null>(null)

  const toggleCategory = (categoryId: string) => {
    setExpandedCategory((prev) => (prev === categoryId ? null : categoryId))
  }

  const balancedCount = data?.balanced_count ?? 0
  const openCount = data?.open_count ?? 0
  const totalDelta = data?.total_delta ?? 0

  return (
    <div>
      <PageHeader title="Kostenabgleich" />

      {isLoading && (
        <p className="mt-6 text-sm text-gray-500">Laden...</p>
      )}

      {isError && (
        <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          Fehler beim Laden der Daten.
        </div>
      )}

      {data && (
        <>
          {/* Summary bar */}
          <div className="mb-6 flex flex-wrap items-center gap-3">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-green-100 px-3 py-1.5 text-sm font-medium text-green-700">
              <Check className="h-4 w-4" />
              {balancedCount} Kategorien ausgeglichen
            </span>
            {openCount > 0 && (
              <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-100 px-3 py-1.5 text-sm font-medium text-amber-700">
                <AlertTriangle className="h-4 w-4" />
                {openCount} Kategorien offen ({formatEur(Math.abs(totalDelta))} nicht berechnet)
              </span>
            )}
          </div>

          {/* Main table */}
          <div className="overflow-x-auto rounded-lg border border-gray-200">
            <table className="min-w-full divide-y divide-gray-200 bg-white text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="w-8 px-4 py-3" />
                  <th className="px-4 py-3 text-left font-medium text-gray-600">Kategorie</th>
                  <th className="px-4 py-3 text-right font-medium text-gray-600">Kosten Gesamt (EUR)</th>
                  <th className="px-4 py-3 text-right font-medium text-gray-600">Berechnet Gesamt</th>
                  <th className="px-4 py-3 text-right font-medium text-gray-600">Delta</th>
                  <th className="px-4 py-3 text-center font-medium text-gray-600">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {data.categories.map((cat) => (
                  <CategoryRow
                    key={cat.category_id}
                    category={cat}
                    isExpanded={expandedCategory === cat.category_id}
                    onToggle={() => toggleCategory(cat.category_id)}
                  />
                ))}
              </tbody>
            </table>
          </div>

          {data.categories.length === 0 && (
            <div className="mt-6 rounded-lg border border-gray-200 bg-white p-8 text-center text-sm text-gray-500">
              Keine Kostenkategorien vorhanden.
            </div>
          )}
        </>
      )}
    </div>
  )
}

// ── Sub-components ──────────────────────────────────────────

function StatusBadge({ status }: { status: string }) {
  if (status === 'balanced') {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">
        <Check className="h-3.5 w-3.5" />
      </span>
    )
  }
  if (status === 'over_invoiced') {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">
        <X className="h-3.5 w-3.5" />
      </span>
    )
  }
  // under_invoiced or other
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-700">
      <AlertTriangle className="h-3.5 w-3.5" />
    </span>
  )
}

function CategoryRow({
  category,
  isExpanded,
  onToggle,
}: {
  category: {
    category_id: string
    category_name: string
    total_provider_costs: number
    total_invoiced: number
    delta: number
    status: string
  }
  isExpanded: boolean
  onToggle: () => void
}) {
  return (
    <>
      <tr
        className="cursor-pointer hover:bg-gray-50"
        onClick={onToggle}
      >
        <td className="px-4 py-3 text-gray-400">
          {isExpanded ? (
            <ChevronDown className="h-4 w-4" />
          ) : (
            <ChevronRight className="h-4 w-4" />
          )}
        </td>
        <td className="px-4 py-3 font-medium text-gray-900">
          {category.category_name}
        </td>
        <td className="px-4 py-3 text-right whitespace-nowrap">
          {formatEur(category.total_provider_costs)}
        </td>
        <td className="px-4 py-3 text-right whitespace-nowrap">
          {formatEur(category.total_invoiced)}
        </td>
        <td className={`px-4 py-3 text-right whitespace-nowrap font-medium ${
          category.delta === 0
            ? 'text-green-700'
            : category.delta > 0
              ? 'text-amber-600'
              : 'text-red-600'
        }`}>
          {formatEur(category.delta)}
        </td>
        <td className="px-4 py-3 text-center">
          <StatusBadge status={category.status} />
        </td>
      </tr>
      {isExpanded && (
        <tr>
          <td colSpan={6} className="bg-gray-50 px-0 py-0">
            <CategoryDetail categoryId={category.category_id} />
          </td>
        </tr>
      )}
    </>
  )
}

function CategoryDetail({ categoryId }: { categoryId: string }) {
  const { data, isLoading, isError } = useCostReconciliationDetail(categoryId)

  if (isLoading) {
    return (
      <div className="px-8 py-4 text-sm text-gray-500">Laden...</div>
    )
  }

  if (isError || !data) {
    return (
      <div className="px-8 py-4 text-sm text-red-600">Fehler beim Laden der Details.</div>
    )
  }

  if (data.provider_invoices.length === 0) {
    return (
      <div className="px-8 py-4 text-sm text-gray-500">Keine Lieferantenrechnungen vorhanden.</div>
    )
  }

  return (
    <div className="px-8 py-4">
      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead>
          <tr>
            <th className="px-3 py-2 text-left font-medium text-gray-500">Rechnung</th>
            <th className="px-3 py-2 text-left font-medium text-gray-500">Datum</th>
            <th className="px-3 py-2 text-right font-medium text-gray-500">Betrag (EUR)</th>
            <th className="px-3 py-2 text-left font-medium text-gray-500">Zugeordnet zu</th>
            <th className="px-3 py-2 text-center font-medium text-gray-500">Status</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {data.provider_invoices.map((inv) => (
            <tr key={inv.id} className="hover:bg-white">
              <td className="px-3 py-2 font-medium">{inv.invoice_number}</td>
              <td className="px-3 py-2">
                {inv.invoice_date ? formatDateGerman(inv.invoice_date) : '\u2014'}
              </td>
              <td className="px-3 py-2 text-right whitespace-nowrap">
                {formatEur(inv.amount_eur)}
              </td>
              <td className="px-3 py-2 text-gray-600">
                {inv.linked_invoice_number ?? '\u2014'}
              </td>
              <td className="px-3 py-2 text-center">
                <InvoiceStatusIcon status={inv.status} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function InvoiceStatusIcon({ status }: { status: string }) {
  if (status === 'linked') {
    return <Check className="mx-auto h-4 w-4 text-green-600" />
  }
  if (status === 'amount_mismatch') {
    return <X className="mx-auto h-4 w-4 text-red-600" />
  }
  // unlinked or other
  return <AlertTriangle className="mx-auto h-4 w-4 text-amber-500" />
}
