import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { MonthSelector } from '@/components/MonthSelector'
import { AmountDisplay } from '@/components/AmountDisplay'
import { StatusBadge } from '@/components/StatusBadge'
import { PageHeader } from '@/components/PageHeader'
import { ErrorAlert } from '@/components/ErrorAlert'
import { useInvoices, useClients, useDashboardOpenInvoices, useDashboardReconciliation, useProviderInvoices } from '@/hooks/useApi'
import { formatMonthYear, formatDateGerman } from '@/utils/format'
import type { InvoiceStatus } from '@/types/api'

export function Dashboard() {
  const now = new Date()
  const [year, setYear] = useState(now.getFullYear())
  const [month, setMonth] = useState(now.getMonth() + 1)
  const [clientId, setClientId] = useState<string | undefined>(undefined)

  const { data: clients } = useClients()
  const { data: invoices, isLoading, isError, error, refetch } = useInvoices({ year, client_id: clientId })
  const { data: openInvoices } = useDashboardOpenInvoices()
  const { data: reconciliation } = useDashboardReconciliation(year, month)
  const { data: providerInvoices } = useProviderInvoices()

  // Smart default: if current month has no data, jump to most recent month with invoices or provider invoices
  const [autoJumped, setAutoJumped] = useState(false)
  useEffect(() => {
    if (invoices && !autoJumped) {
      const currentMonthHasData = invoices.some(
        (inv) => inv.period_year === year && inv.period_month === month,
      )

      // Also check if provider invoices exist for this month
      const monthStr = `${year}-${String(month).padStart(2, '0')}`
      const hasProviderData = providerInvoices?.some((pi) => pi.assigned_month === monthStr)

      if (!currentMonthHasData && !hasProviderData) {
        // Collect all months with any data
        const months: { year: number; month: number }[] = []
        for (const inv of invoices) {
          months.push({ year: inv.period_year, month: inv.period_month })
        }
        if (providerInvoices) {
          for (const pi of providerInvoices) {
            if (pi.assigned_month) {
              const [y, m] = pi.assigned_month.split('-').map(Number)
              if (y && m) months.push({ year: y, month: m })
            }
          }
        }
        if (months.length > 0) {
          const sorted = months.sort((a, b) => {
            if (a.year !== b.year) return b.year - a.year
            return b.month - a.month
          })
          const latest = sorted[0]
          if (latest) {
            setYear(latest.year)
            setMonth(latest.month)
          }
        }
      }
      setAutoJumped(true)
    }
  }, [invoices, providerInvoices, autoJumped, year, month])

  const monthInvoices = invoices?.filter(
    (inv) => inv.period_year === year && inv.period_month === month,
  ) ?? []

  const allYearInvoices = invoices ?? []

  const statusCounts = allYearInvoices.reduce(
    (acc, inv) => {
      acc[inv.status as InvoiceStatus] = (acc[inv.status as InvoiceStatus] ?? 0) + 1
      return acc
    },
    {} as Record<InvoiceStatus, number>,
  )

  const yearNetTotal = allYearInvoices.reduce((sum, inv) => sum + inv.net_total, 0)
  const yearGrossTotal = allYearInvoices.reduce((sum, inv) => sum + inv.gross_total, 0)

  return (
    <div>
      <PageHeader
        title="Dashboard"
        action={
          <Link
            to="/invoices/generate"
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            Rechnung erstellen
          </Link>
        }
      />

      <div className="flex flex-wrap items-end gap-4">
        <MonthSelector
          year={year}
          month={month}
          onChange={(y, m) => { setYear(y); setMonth(m) }}
        />
        {clients && clients.length > 1 && (
          <select
            value={clientId ?? ''}
            onChange={(e) => setClientId(e.target.value || undefined)}
            title="Kunde filtern"
            className="rounded-md border border-gray-300 px-3 py-1.5 text-sm"
          >
            <option value="">Alle Kunden</option>
            {clients.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
        )}
      </div>

      {isError && <ErrorAlert error={error} onRetry={() => void refetch()} />}

      {/* Summary cards */}
      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <SummaryCard
          label={`Rechnungen ${year}`}
          value={String(allYearInvoices.length)}
        />
        <SummaryCard
          label="Netto Gesamt"
          value={<AmountDisplay amount={yearNetTotal} />}
        />
        <SummaryCard
          label="Brutto Gesamt"
          value={<AmountDisplay amount={yearGrossTotal} />}
        />
        <SummaryCard
          label="Offene Rechnungen"
          value={
            openInvoices ? (
              <div>
                <span>{openInvoices.count}</span>
                {openInvoices.count > 0 && (
                  <span className="ml-2 text-sm font-normal text-gray-500">
                    (<AmountDisplay amount={openInvoices.total_gross} />)
                  </span>
                )}
              </div>
            ) : '-'
          }
        />
        <SummaryCard
          label="Status"
          value={
            <div className="flex flex-wrap gap-1.5">
              {(Object.entries(statusCounts) as [InvoiceStatus, number][]).map(([s, c]) => (
                <span key={s} className="text-xs">
                  <StatusBadge status={s} /> {c}
                </span>
              ))}
              {Object.keys(statusCounts).length === 0 && (
                <span className="text-xs text-gray-400">Keine</span>
              )}
            </div>
          }
        />
      </div>

      {/* Month invoices */}
      <div className="mt-8">
        <h2 className="mb-3 text-lg font-semibold text-gray-800">
          {formatMonthYear(year, month)}
        </h2>

        {isLoading ? (
          <p className="text-sm text-gray-500">Laden...</p>
        ) : monthInvoices.length === 0 ? (
          <div className="rounded-lg border border-gray-200 bg-white p-6 text-center text-sm text-gray-500">
            Keine Rechnungen für diesen Monat.{' '}
            <Link to="/invoices/generate" className="text-blue-600 hover:underline">
              Jetzt erstellen
            </Link>
          </div>
        ) : (
          <div className="overflow-x-auto rounded-lg border border-gray-200">
            <table className="min-w-full divide-y divide-gray-200 bg-white text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">Rechnung</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">Datum</th>
                  <th className="px-4 py-3 text-right font-medium text-gray-600">Netto</th>
                  <th className="px-4 py-3 text-right font-medium text-gray-600">Brutto</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {monthInvoices.map((inv) => (
                  <tr key={inv.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <Link to={`/invoices/${inv.id}`} className="text-blue-600 hover:underline">
                        {inv.invoice_number}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-gray-600">{formatDateGerman(inv.invoice_date)}</td>
                    <td className="px-4 py-3 text-right"><AmountDisplay amount={inv.net_total} /></td>
                    <td className="px-4 py-3 text-right"><AmountDisplay amount={inv.gross_total} /></td>
                    <td className="px-4 py-3"><StatusBadge status={inv.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Reconciliation summary */}
      {reconciliation && (
        <div className="mt-8">
          <div className="flex items-center justify-between">
            <h2 className="mb-3 text-lg font-semibold text-gray-800">
              Abstimmung {formatMonthYear(year, month)}
            </h2>
            <Link to="/reconciliation" className="text-sm text-blue-600 hover:underline">
              Details
            </Link>
          </div>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <SummaryCard
              label="Lieferantenrechnungen abgeglichen"
              value={`${reconciliation.matched_count} / ${reconciliation.matched_count + reconciliation.unmatched_count}`}
            />
            <SummaryCard
              label="Nicht zugeordnete Banktransaktionen"
              value={String(reconciliation.unmatched_bank_transactions.length)}
            />
            <SummaryCard
              label="Rechnungsstatus"
              value={
                reconciliation.invoice_status ? (
                  <div className="text-sm">
                    <span>{reconciliation.invoice_status.status}</span>
                    {reconciliation.invoice_status.balance !== 0 && (
                      <span className="ml-2 text-gray-500">
                        Offen: <AmountDisplay amount={reconciliation.invoice_status.balance} />
                      </span>
                    )}
                  </div>
                ) : (
                  <span className="text-gray-400">Keine Rechnung</span>
                )
              }
            />
          </div>
        </div>
      )}

      {/* Quick links */}
      <div className="mt-8 grid grid-cols-2 gap-3 sm:grid-cols-5">
        <QuickLink to="/bank-transactions" label="Bank importieren" />
        <QuickLink to="/upwork-transactions" label="Upwork importieren" />
        <QuickLink to="/provider-invoices" label="Lieferantenrechnungen" />
        <QuickLink to="/payments" label="Zahlungen" />
        <QuickLink to="/reconciliation" label="Abstimmung" />
      </div>
    </div>
  )
}

function SummaryCard({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white px-4 py-5">
      <p className="text-xs font-medium text-gray-500">{label}</p>
      <div className="mt-1 text-lg font-semibold text-gray-900">{value}</div>
    </div>
  )
}

function QuickLink({ to, label }: { to: string; label: string }) {
  return (
    <Link
      to={to}
      className="rounded-lg border border-gray-200 bg-white px-4 py-3 text-center text-sm font-medium text-gray-700 hover:border-blue-300 hover:text-blue-600"
    >
      {label}
    </Link>
  )
}
