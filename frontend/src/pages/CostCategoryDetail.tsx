import { useParams, Link } from 'react-router-dom'
import { PageHeader } from '@/components/PageHeader'
import { AmountDisplay } from '@/components/AmountDisplay'
import { useCostCategory, useProviderInvoices, useBankTransactions } from '@/hooks/useApi'
import { formatDateGerman } from '@/utils/format'

export function CostCategoryDetail() {
  const { id } = useParams<{ id: string }>()
  const { data: category, isLoading } = useCostCategory(id ?? '')
  const { data: invoices } = useProviderInvoices({ category_id: id })
  const { data: bankTxns } = useBankTransactions({ category_id: id })

  if (isLoading) return <p className="text-sm text-gray-500">Laden...</p>
  if (!category) return <p className="text-sm text-red-600">Kategorie nicht gefunden.</p>

  return (
    <div>
      <PageHeader
        title={category.name}
        action={
          <Link
            to="/categories"
            className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Zur\u00FCck
          </Link>
        }
      />

      {/* Category details */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-3">
        <Field label="ID" value={category.id} />
        <Field label="Anbieter" value={category.provider_name ?? '-'} />
        <Field label="Standort" value={category.provider_location ?? '-'} />
        <Field label="Kostentyp" value={category.cost_type} />
        <Field label="Abrechnungszyklus" value={category.billing_cycle} />
        <Field label="W\u00E4hrung" value={category.currency} />
        <Field label="USt-Status" value={category.vat_status} />
        <Field label="Verteilungsmethode" value={category.distribution_method ?? '-'} />
        <Field label="Sortierung" value={String(category.sort_order)} />
      </div>

      {/* Bank keywords */}
      <div className="mt-6">
        <h3 className="mb-2 text-sm font-semibold text-gray-700">Bank-Schl\u00FCsselw\u00F6rter</h3>
        <div className="flex flex-wrap gap-2">
          {category.bank_keywords.length === 0 ? (
            <span className="text-sm text-gray-400">Keine</span>
          ) : (
            category.bank_keywords.map((kw) => (
              <span key={kw} className="rounded-full bg-gray-200 px-3 py-1 text-xs font-medium text-gray-700">
                {kw}
              </span>
            ))
          )}
        </div>
      </div>

      {/* Notes */}
      {category.notes && (
        <div className="mt-4 text-sm text-gray-600">
          <span className="font-medium">Notizen:</span> {category.notes}
        </div>
      )}

      {/* Provider invoices */}
      <div className="mt-8">
        <h3 className="mb-3 text-sm font-semibold text-gray-700">
          Lieferantenrechnungen ({invoices?.length ?? 0})
        </h3>
        {invoices && invoices.length > 0 ? (
          <div className="overflow-x-auto rounded-lg border border-gray-200">
            <table className="min-w-full divide-y divide-gray-200 bg-white text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 text-left font-medium text-gray-600">Nr.</th>
                  <th className="px-4 py-2 text-left font-medium text-gray-600">Datum</th>
                  <th className="px-4 py-2 text-right font-medium text-gray-600">Betrag</th>
                  <th className="px-4 py-2 text-left font-medium text-gray-600">Zugeordneter Monat</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {invoices.map((inv) => (
                  <tr key={inv.id}>
                    <td className="px-4 py-2">{inv.invoice_number}</td>
                    <td className="px-4 py-2 text-gray-600">{formatDateGerman(inv.invoice_date)}</td>
                    <td className="px-4 py-2 text-right"><AmountDisplay amount={inv.amount} /></td>
                    <td className="px-4 py-2 text-gray-600">{inv.assigned_month ?? '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-sm text-gray-400">Keine Lieferantenrechnungen.</p>
        )}
      </div>

      {/* Bank transactions */}
      <div className="mt-8">
        <h3 className="mb-3 text-sm font-semibold text-gray-700">
          Banktransaktionen ({bankTxns?.length ?? 0})
        </h3>
        {bankTxns && bankTxns.length > 0 ? (
          <div className="overflow-x-auto rounded-lg border border-gray-200">
            <table className="min-w-full divide-y divide-gray-200 bg-white text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 text-left font-medium text-gray-600">Buchungstag</th>
                  <th className="px-4 py-2 text-left font-medium text-gray-600">Beschreibung</th>
                  <th className="px-4 py-2 text-right font-medium text-gray-600">Betrag</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {bankTxns.map((tx) => (
                  <tr key={tx.id}>
                    <td className="px-4 py-2">{formatDateGerman(tx.booking_date)}</td>
                    <td className="px-4 py-2 text-gray-600 max-w-md truncate">{tx.description}</td>
                    <td className="px-4 py-2 text-right"><AmountDisplay amount={tx.amount_eur} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-sm text-gray-400">Keine Banktransaktionen.</p>
        )}
      </div>
    </div>
  )
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white px-4 py-3">
      <p className="text-xs font-medium text-gray-500">{label}</p>
      <p className="mt-1 text-sm text-gray-900">{value}</p>
    </div>
  )
}
