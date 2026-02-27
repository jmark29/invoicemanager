import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { PageHeader } from '@/components/PageHeader'
import { AmountDisplay } from '@/components/AmountDisplay'
import { StatusBadge } from '@/components/StatusBadge'
import { ErrorAlert } from '@/components/ErrorAlert'
import { ConfirmDialog } from '@/components/ConfirmDialog'
import { useInvoice, useUpdateInvoiceStatus, usePayments, useRegenerateInvoice } from '@/hooks/useApi'
import { formatDateGerman, formatMonthYear } from '@/utils/format'
import type { InvoiceStatus } from '@/types/api'

const STATUSES: InvoiceStatus[] = ['draft', 'sent', 'paid', 'overdue']

export function InvoiceDetail() {
  const { id } = useParams<{ id: string }>()
  const invoiceId = Number(id)
  const { data: invoice, isLoading, isError, error, refetch } = useInvoice(invoiceId)
  const { data: payments } = usePayments({ matched_invoice_id: invoiceId })
  const statusMutation = useUpdateInvoiceStatus()
  const regenerateMutation = useRegenerateInvoice()
  const [showRegenConfirm, setShowRegenConfirm] = useState(false)

  if (isLoading) return <p className="text-sm text-gray-500">Laden...</p>
  if (isError) return <ErrorAlert error={error} onRetry={() => void refetch()} />
  if (!invoice) return <p className="text-sm text-red-600">Rechnung nicht gefunden.</p>

  const canRegenerate = invoice.status === 'draft' || invoice.status === 'overdue'

  const handleRegenerate = () => {
    setShowRegenConfirm(false)
    regenerateMutation.mutate(
      { id: invoiceId, data: { notes: invoice.notes } },
      { onSuccess: () => void refetch() },
    )
  }

  const handleStatusChange = (newStatus: InvoiceStatus) => {
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
        title={`Rechnung ${invoice.invoice_number}`}
        action={
          <div className="flex gap-2">
            {canRegenerate && (
              <button
                type="button"
                onClick={() => setShowRegenConfirm(true)}
                disabled={regenerateMutation.isPending}
                className="rounded-md bg-amber-600 px-4 py-2 text-sm font-medium text-white hover:bg-amber-700 disabled:opacity-50"
              >
                {regenerateMutation.isPending ? 'Generiere...' : 'Neu generieren'}
              </button>
            )}
            <a
              href={`/api/invoices/${invoiceId}/download`}
              target="_blank"
              rel="noopener noreferrer"
              className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
            >
              PDF herunterladen
            </a>
            <Link
              to="/invoices"
              className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Zur\u00FCck
            </Link>
          </div>
        }
      />

      {/* Header info */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <InfoCard label="Zeitraum" value={formatMonthYear(invoice.period_year, invoice.period_month)} />
        <InfoCard label="Rechnungsdatum" value={formatDateGerman(invoice.invoice_date)} />
        <InfoCard
          label="Status"
          value={
            <div className="flex items-center gap-2">
              <StatusBadge status={invoice.status} />
              <select
                value={invoice.status}
                onChange={(e) => handleStatusChange(e.target.value as InvoiceStatus)}
                className="rounded border border-gray-300 px-1.5 py-0.5 text-xs"
              >
                {STATUSES.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>
          }
        />
        <InfoCard
          label="Erstellt"
          value={formatDateGerman(invoice.created_at)}
        />
      </div>

      {/* Line items */}
      <div className="mt-6">
        <h2 className="mb-3 text-sm font-semibold text-gray-700">Positionen</h2>
        <div className="overflow-x-auto rounded-lg border border-gray-200">
          <table className="min-w-full divide-y divide-gray-200 bg-white text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="w-12 px-4 py-3 text-left font-medium text-gray-600">Pos</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Bezeichnung</th>
                <th className="w-24 px-4 py-3 text-left font-medium text-gray-600">Typ</th>
                <th className="w-40 px-4 py-3 text-right font-medium text-gray-600">Betrag</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {invoice.items
                .sort((a, b) => a.position - b.position)
                .map((item) => (
                  <tr key={item.id}>
                    <td className="px-4 py-3 text-gray-500">{item.position}</td>
                    <td className="px-4 py-3">{item.label}</td>
                    <td className="px-4 py-3 text-xs text-gray-500">{item.source_type}</td>
                    <td className="px-4 py-3 text-right">
                      <AmountDisplay amount={item.amount} />
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Totals */}
      <div className="mt-4 flex justify-end">
        <div className="w-80 space-y-1 text-sm">
          <div className="flex justify-between border-t border-gray-200 pt-2">
            <span className="text-gray-600">Netto-Rechnungsbetrag</span>
            <AmountDisplay amount={invoice.net_total} className="font-medium" />
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">Umsatzsteuer 19%</span>
            <AmountDisplay amount={invoice.vat_amount} />
          </div>
          <div className="flex justify-between border-t border-gray-300 pt-2 font-bold">
            <span>Brutto-Rechnungsbetrag</span>
            <AmountDisplay amount={invoice.gross_total} className="font-bold" />
          </div>
        </div>
      </div>

      {/* Notes */}
      {invoice.notes && (
        <div className="mt-6">
          <h2 className="mb-2 text-sm font-semibold text-gray-700">Notizen</h2>
          <p className="text-sm text-gray-600">{invoice.notes}</p>
        </div>
      )}

      {/* Payments */}
      {payments && payments.length > 0 && (
        <div className="mt-6">
          <h2 className="mb-3 text-sm font-semibold text-gray-700">Zahlungen</h2>
          <div className="overflow-x-auto rounded-lg border border-gray-200">
            <table className="min-w-full divide-y divide-gray-200 bg-white text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">Datum</th>
                  <th className="px-4 py-3 text-right font-medium text-gray-600">Betrag</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">Referenz</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {payments.map((p) => (
                  <tr key={p.id}>
                    <td className="px-4 py-3">{formatDateGerman(p.payment_date)}</td>
                    <td className="px-4 py-3 text-right"><AmountDisplay amount={p.amount_eur} /></td>
                    <td className="px-4 py-3 text-gray-600">{p.reference ?? '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {regenerateMutation.isError && (
        <div className="mt-4">
          <ErrorAlert error={regenerateMutation.error} />
        </div>
      )}

      <ConfirmDialog
        open={showRegenConfirm}
        title="Rechnung neu generieren"
        message="Die bestehende PDF wird archiviert und die Rechnung mit aktuellen Daten neu generiert. Fortfahren?"
        onConfirm={handleRegenerate}
        onCancel={() => setShowRegenConfirm(false)}
        confirmLabel="Neu generieren"
      />
    </div>
  )
}

function InfoCard({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white px-4 py-3">
      <p className="text-xs font-medium text-gray-500">{label}</p>
      <div className="mt-1 text-sm font-medium text-gray-900">{value}</div>
    </div>
  )
}
