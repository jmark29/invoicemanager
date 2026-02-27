import { useState } from 'react'
import { MonthSelector } from '@/components/MonthSelector'
import { AmountDisplay } from '@/components/AmountDisplay'
import { PageHeader } from '@/components/PageHeader'
import { ErrorAlert } from '@/components/ErrorAlert'
import { useDashboardReconciliation } from '@/hooks/useApi'
import { formatMonthYear, formatDateGerman } from '@/utils/format'

export function Reconciliation() {
  const now = new Date()
  const [year, setYear] = useState(now.getFullYear())
  const [month, setMonth] = useState(now.getMonth() + 1)

  const { data, isLoading, isError, error, refetch } = useDashboardReconciliation(year, month)

  return (
    <div>
      <PageHeader title="Abstimmung" />

      <MonthSelector
        year={year}
        month={month}
        onChange={(y, m) => { setYear(y); setMonth(m) }}
      />

      {isError && <ErrorAlert error={error} onRetry={() => void refetch()} />}

      {isLoading ? (
        <p className="mt-6 text-sm text-gray-500">Laden...</p>
      ) : data ? (
        <div className="mt-6 space-y-8">
          {/* Summary cards */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div className="rounded-lg border border-gray-200 bg-white px-4 py-5">
              <p className="text-xs font-medium text-gray-500">Abgeglichen</p>
              <div className="mt-1 text-lg font-semibold text-green-700">
                {data.matched_count} von {data.matched_count + data.unmatched_count}
              </div>
            </div>
            <div className="rounded-lg border border-gray-200 bg-white px-4 py-5">
              <p className="text-xs font-medium text-gray-500">Nicht zugeordnet (Bank)</p>
              <div className={`mt-1 text-lg font-semibold ${data.unmatched_bank_transactions.length > 0 ? 'text-amber-600' : 'text-gray-900'}`}>
                {data.unmatched_bank_transactions.length}
              </div>
            </div>
            <div className="rounded-lg border border-gray-200 bg-white px-4 py-5">
              <p className="text-xs font-medium text-gray-500">Rechnungsstatus</p>
              <div className="mt-1 text-lg font-semibold text-gray-900">
                {data.invoice_status ? data.invoice_status.status : 'Keine Rechnung'}
              </div>
            </div>
          </div>

          {/* Provider invoices vs bank payments */}
          <div>
            <h2 className="mb-3 text-sm font-semibold text-gray-700">
              Lieferantenrechnungen vs. Bankzahlungen — {formatMonthYear(year, month)}
            </h2>
            {data.provider_matches.length === 0 ? (
              <div className="rounded-lg border border-gray-200 bg-white p-6 text-center text-sm text-gray-500">
                Keine Lieferantenrechnungen für diesen Monat.
              </div>
            ) : (
              <div className="overflow-x-auto rounded-lg border border-gray-200">
                <table className="min-w-full divide-y divide-gray-200 bg-white text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left font-medium text-gray-600">Kategorie</th>
                      <th className="px-4 py-3 text-left font-medium text-gray-600">Rechnung</th>
                      <th className="px-4 py-3 text-right font-medium text-gray-600">Rechnungsbetrag</th>
                      <th className="px-4 py-3 text-center font-medium text-gray-600">Bankzahlung</th>
                      <th className="px-4 py-3 text-right font-medium text-gray-600">Bankbetrag</th>
                      <th className="px-4 py-3 text-left font-medium text-gray-600">Buchungsdatum</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {data.provider_matches.map((match, i) => (
                      <tr key={i} className={match.has_bank_payment ? 'hover:bg-gray-50' : 'bg-amber-50'}>
                        <td className="px-4 py-3 text-gray-700">{match.category_name}</td>
                        <td className="px-4 py-3 font-medium">{match.invoice_number}</td>
                        <td className="px-4 py-3 text-right">
                          <AmountDisplay amount={match.invoice_amount} />
                        </td>
                        <td className="px-4 py-3 text-center">
                          {match.has_bank_payment ? (
                            <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-green-100 text-green-700 text-xs">&#10003;</span>
                          ) : (
                            <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-red-100 text-red-700 text-xs">&#10007;</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-right">
                          {match.bank_amount != null ? <AmountDisplay amount={match.bank_amount} /> : '-'}
                        </td>
                        <td className="px-4 py-3 text-gray-600">
                          {match.bank_booking_date ? formatDateGerman(match.bank_booking_date) : '-'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Unmatched bank transactions */}
          {data.unmatched_bank_transactions.length > 0 && (
            <div>
              <h2 className="mb-3 text-sm font-semibold text-gray-700">
                Nicht zugeordnete Banktransaktionen
              </h2>
              <div className="overflow-x-auto rounded-lg border border-amber-200">
                <table className="min-w-full divide-y divide-gray-200 bg-white text-sm">
                  <thead className="bg-amber-50">
                    <tr>
                      <th className="px-4 py-3 text-left font-medium text-gray-600">Buchungstag</th>
                      <th className="px-4 py-3 text-right font-medium text-gray-600">Betrag</th>
                      <th className="px-4 py-3 text-left font-medium text-gray-600">Beschreibung</th>
                      <th className="px-4 py-3 text-left font-medium text-gray-600">Kategorie</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {data.unmatched_bank_transactions.map((tx) => (
                      <tr key={tx.id} className="hover:bg-gray-50">
                        <td className="px-4 py-3 whitespace-nowrap">{formatDateGerman(tx.booking_date)}</td>
                        <td className="px-4 py-3 text-right whitespace-nowrap">
                          <AmountDisplay amount={tx.amount_eur} />
                        </td>
                        <td className="px-4 py-3 max-w-xs truncate" title={tx.description}>
                          {tx.description}
                        </td>
                        <td className="px-4 py-3 text-gray-500">{tx.category_id ?? '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Invoice payment status */}
          {data.invoice_status && (
            <div>
              <h2 className="mb-3 text-sm font-semibold text-gray-700">Rechnungszahlung</h2>
              <div className="rounded-lg border border-gray-200 bg-white p-5">
                <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                  <div>
                    <p className="text-xs text-gray-500">Rechnung</p>
                    <p className="mt-1 font-medium">{data.invoice_status.invoice_number}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">Brutto</p>
                    <p className="mt-1 font-medium"><AmountDisplay amount={data.invoice_status.gross_total} /></p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">Bezahlt</p>
                    <p className="mt-1 font-medium"><AmountDisplay amount={data.invoice_status.total_paid} /></p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">Offen</p>
                    <p className={`mt-1 font-medium ${data.invoice_status.balance > 0 ? 'text-amber-600' : 'text-green-700'}`}>
                      <AmountDisplay amount={data.invoice_status.balance} />
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="mt-6 rounded-lg border border-gray-200 bg-white p-8 text-center text-sm text-gray-500">
          Keine Daten für {formatMonthYear(year, month)}.
        </div>
      )}
    </div>
  )
}
