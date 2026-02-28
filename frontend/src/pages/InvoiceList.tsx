import { useState } from 'react'
import { Link } from 'react-router-dom'
import { PageHeader } from '@/components/PageHeader'
import { StatusBadge } from '@/components/StatusBadge'
import { AmountDisplay } from '@/components/AmountDisplay'
import { ErrorAlert } from '@/components/ErrorAlert'
import { PDFPreviewModal } from '@/components/PDFPreviewModal'
import { useInvoices, useClients, useUpdateInvoiceStatus } from '@/hooks/useApi'
import { formatDateGerman, formatMonthYear } from '@/utils/format'
import type { InvoiceStatus } from '@/types/api'

const STATUSES: InvoiceStatus[] = ['draft', 'sent', 'paid', 'overdue']

export function InvoiceList() {
  const now = new Date()
  const [yearFilter, setYearFilter] = useState<number | undefined>(now.getFullYear())
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined)
  const [clientFilter, setClientFilter] = useState<string | undefined>(undefined)

  const { data: invoices, isLoading, isError, error, refetch } = useInvoices({
    year: yearFilter,
    status: statusFilter,
    client_id: clientFilter,
  })
  const { data: clients } = useClients()
  const statusMutation = useUpdateInvoiceStatus()
  const [previewInv, setPreviewInv] = useState<{ id: number; label: string } | null>(null)

  const handleStatusChange = (invoiceId: number, newStatus: InvoiceStatus) => {
    statusMutation.mutate({
      id: invoiceId,
      data: {
        status: newStatus,
        sent_date: newStatus === 'sent' ? new Date().toISOString().split('T')[0] : undefined,
      },
    })
  }

  return (
    <div>
      <PageHeader
        title="Rechnungen"
        action={
          <Link
            to="/invoices/generate"
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            Neue Rechnung
          </Link>
        }
      />

      {/* Filters */}
      <div className="mb-4 flex flex-wrap gap-3">
        <select
          value={yearFilter ?? ''}
          onChange={(e) => setYearFilter(e.target.value ? Number(e.target.value) : undefined)}
          title="Jahr filtern"
          className="rounded-md border border-gray-300 px-3 py-1.5 text-sm"
        >
          <option value="">Alle Jahre</option>
          {Array.from({ length: 5 }, (_, i) => now.getFullYear() - 2 + i).map((y) => (
            <option key={y} value={y}>{y}</option>
          ))}
        </select>

        <select
          value={statusFilter ?? ''}
          onChange={(e) => setStatusFilter(e.target.value || undefined)}
          title="Status filtern"
          className="rounded-md border border-gray-300 px-3 py-1.5 text-sm"
        >
          <option value="">Alle Status</option>
          {STATUSES.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>

        <select
          value={clientFilter ?? ''}
          onChange={(e) => setClientFilter(e.target.value || undefined)}
          title="Kunde filtern"
          className="rounded-md border border-gray-300 px-3 py-1.5 text-sm"
        >
          <option value="">Alle Kunden</option>
          {clients?.map((c) => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>
      </div>

      {/* Table */}
      {isError ? (
        <ErrorAlert error={error} onRetry={() => void refetch()} />
      ) : isLoading ? (
        <p className="text-sm text-gray-500">Laden...</p>
      ) : !invoices || invoices.length === 0 ? (
        <div className="rounded-lg border border-gray-200 bg-white p-8 text-center text-sm text-gray-500">
          Keine Rechnungen gefunden.
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-gray-200">
          <table className="min-w-full divide-y divide-gray-200 bg-white text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Rechnung</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Zeitraum</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Datum</th>
                <th className="px-4 py-3 text-right font-medium text-gray-600">Netto</th>
                <th className="px-4 py-3 text-right font-medium text-gray-600">Brutto</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Status</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Aktionen</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {invoices.map((inv) => (
                <tr key={inv.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <Link to={`/invoices/${inv.id}`} className="text-blue-600 hover:underline">
                      {inv.invoice_number}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-gray-600">
                    {formatMonthYear(inv.period_year, inv.period_month)}
                  </td>
                  <td className="px-4 py-3 text-gray-600">
                    {formatDateGerman(inv.invoice_date)}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <AmountDisplay amount={inv.net_total} />
                  </td>
                  <td className="px-4 py-3 text-right font-medium">
                    <AmountDisplay amount={inv.gross_total} />
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={inv.status} />
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => setPreviewInv({ id: inv.id, label: inv.invoice_number })}
                        className="text-xs text-blue-600 hover:underline"
                      >
                        PDF
                      </button>
                      <select
                        value={inv.status}
                        onChange={(e) => handleStatusChange(inv.id, e.target.value as InvoiceStatus)}
                        title="Status ändern"
                        className="rounded border border-gray-300 px-1.5 py-0.5 text-xs"
                      >
                        {STATUSES.map((s) => (
                          <option key={s} value={s}>{s}</option>
                        ))}
                      </select>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {previewInv && (
        <PDFPreviewModal
          url={`/api/invoices/${previewInv.id}/download`}
          title={`Rechnung ${previewInv.label}`}
          onClose={() => setPreviewInv(null)}
        />
      )}
    </div>
  )
}
