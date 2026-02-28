import { useState } from 'react'
import { Link } from 'react-router-dom'
import { PageHeader } from '@/components/PageHeader'
import { AmountDisplay } from '@/components/AmountDisplay'
import { ConfirmDialog } from '@/components/ConfirmDialog'
import { ErrorAlert } from '@/components/ErrorAlert'
import { usePayments, useClients, useInvoices, useCreatePayment, useDeletePayment } from '@/hooks/useApi'
import { formatDateGerman, todayISO } from '@/utils/format'

export function Payments() {
  const { data: payments, isLoading, isError, error, refetch } = usePayments()
  const { data: clients } = useClients(true)
  const { data: invoices } = useInvoices()
  const createMutation = useCreatePayment()
  const deleteMutation = useDeletePayment()

  const [showForm, setShowForm] = useState(false)
  const [deleteId, setDeleteId] = useState<number | null>(null)

  // Form state
  const [clientId, setClientId] = useState('')
  const [paymentDate, setPaymentDate] = useState(todayISO())
  const [amount, setAmount] = useState('')
  const [reference, setReference] = useState('')
  const [matchedInvoiceId, setMatchedInvoiceId] = useState<string>('')
  const [notes, setNotes] = useState('')

  const handleCreate = async () => {
    if (!clientId || !amount) return
    await createMutation.mutateAsync({
      client_id: clientId,
      payment_date: paymentDate,
      amount_eur: parseFloat(amount),
      reference: reference || undefined,
      matched_invoice_id: matchedInvoiceId ? Number(matchedInvoiceId) : undefined,
      notes: notes || undefined,
    })
    setShowForm(false)
    setClientId('')
    setAmount('')
    setReference('')
    setMatchedInvoiceId('')
    setNotes('')
  }

  const handleDelete = () => {
    if (deleteId !== null) {
      deleteMutation.mutate(deleteId)
      setDeleteId(null)
    }
  }

  return (
    <div>
      <PageHeader
        title="Zahlungen"
        action={
          <button
            onClick={() => setShowForm(!showForm)}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            {showForm ? 'Abbrechen' : 'Zahlung erfassen'}
          </button>
        }
      />

      {/* Create form */}
      {showForm && (
        <div className="mb-6 rounded-lg border border-gray-200 bg-white p-5">
          <h2 className="mb-4 text-sm font-semibold text-gray-700">Neue Zahlung</h2>
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-3">
            <div>
              <label className="block text-xs font-medium text-gray-600">Kunde</label>
              <select
                value={clientId}
                onChange={(e) => setClientId(e.target.value)}
                className="mt-1 w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm"
              >
                <option value="">-- Wählen --</option>
                {clients?.map((c) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600">Zahlungsdatum</label>
              <input
                type="date"
                value={paymentDate}
                onChange={(e) => setPaymentDate(e.target.value)}
                className="mt-1 w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600">Betrag (EUR)</label>
              <input
                type="number"
                step="0.01"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                className="mt-1 w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600">Referenz</label>
              <input
                type="text"
                value={reference}
                onChange={(e) => setReference(e.target.value)}
                className="mt-1 w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600">Rechnung zuordnen</label>
              <select
                value={matchedInvoiceId}
                onChange={(e) => setMatchedInvoiceId(e.target.value)}
                className="mt-1 w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm"
              >
                <option value="">-- Keine --</option>
                {invoices?.map((inv) => (
                  <option key={inv.id} value={inv.id}>{inv.invoice_number}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600">Notizen</label>
              <input
                type="text"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                className="mt-1 w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm"
              />
            </div>
          </div>
          <div className="mt-4">
            <button
              onClick={() => void handleCreate()}
              disabled={!clientId || !amount || createMutation.isPending}
              className="rounded-md bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
            >
              {createMutation.isPending ? 'Speichere...' : 'Zahlung speichern'}
            </button>
          </div>
        </div>
      )}

      {/* Table */}
      {isError ? (
        <ErrorAlert error={error} onRetry={() => void refetch()} />
      ) : isLoading ? (
        <p className="text-sm text-gray-500">Laden...</p>
      ) : !payments || payments.length === 0 ? (
        <div className="rounded-lg border border-gray-200 bg-white p-8 text-center text-sm text-gray-500">
          Keine Zahlungen erfasst.
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-gray-200">
          <table className="min-w-full divide-y divide-gray-200 bg-white text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Datum</th>
                <th className="px-4 py-3 text-right font-medium text-gray-600">Betrag</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Referenz</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Rechnung</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Notizen</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Aktionen</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {payments.map((p) => (
                <tr key={p.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">{formatDateGerman(p.payment_date)}</td>
                  <td className="px-4 py-3 text-right"><AmountDisplay amount={p.amount_eur} /></td>
                  <td className="px-4 py-3 text-gray-600">{p.reference ?? '-'}</td>
                  <td className="px-4 py-3">
                    {p.matched_invoice_id ? (
                      <Link to={`/invoices/${p.matched_invoice_id}`} className="text-blue-600 hover:underline">
                        #{p.matched_invoice_id}
                      </Link>
                    ) : (
                      <span className="text-gray-400">-</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-gray-600">{p.notes ?? '-'}</td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => setDeleteId(p.id)}
                      className="text-xs text-red-600 hover:underline"
                    >
                      Löschen
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <ConfirmDialog
        open={deleteId !== null}
        title="Zahlung löschen"
        message="Möchten Sie diese Zahlung wirklich löschen?"
        onConfirm={handleDelete}
        onCancel={() => setDeleteId(null)}
        confirmLabel="Löschen"
      />
    </div>
  )
}
