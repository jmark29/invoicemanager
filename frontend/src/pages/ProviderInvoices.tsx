import { useState, useRef } from 'react'
import { PageHeader } from '@/components/PageHeader'
import { AmountDisplay } from '@/components/AmountDisplay'
import { ErrorAlert } from '@/components/ErrorAlert'
import { ConfirmDialog } from '@/components/ConfirmDialog'
import { PDFPreviewModal } from '@/components/PDFPreviewModal'
import { BulkUploadZone } from '@/components/BulkUploadZone'
import { Upload, Download, Eye, RefreshCw, Pencil, Trash2 } from 'lucide-react'
import {
  useProviderInvoices, useCostCategories,
  useUploadProviderInvoicePdf, useCreateProviderInvoice,
  useUpdateProviderInvoice, useDeleteProviderInvoice,
} from '@/hooks/useApi'
import { formatDateGerman, todayISO } from '@/utils/format'
import type { ProviderInvoice } from '@/types/api'

interface InvoiceForm {
  category_id: string
  invoice_number: string
  invoice_date: string
  amount: string
  currency: string
  assigned_month: string
}

const emptyForm: InvoiceForm = {
  category_id: '',
  invoice_number: '',
  invoice_date: todayISO(),
  amount: '',
  currency: 'EUR',
  assigned_month: '',
}

export function ProviderInvoices() {
  const [categoryFilter, setCategoryFilter] = useState<string | undefined>(undefined)
  const [monthFilter, setMonthFilter] = useState<string | undefined>(undefined)

  const { data: invoices, isLoading, isError, error, refetch } = useProviderInvoices({
    category_id: categoryFilter,
    assigned_month: monthFilter,
  })
  const { data: categories } = useCostCategories()
  const uploadMutation = useUploadProviderInvoicePdf()
  const createMutation = useCreateProviderInvoice()
  const updateMutation = useUpdateProviderInvoice()
  const deleteMutation = useDeleteProviderInvoice()
  const fileInputRefs = useRef<Record<number, HTMLInputElement | null>>({})

  const [previewInv, setPreviewInv] = useState<{ id: number; label: string } | null>(null)
  const [showCreate, setShowCreate] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [form, setForm] = useState<InvoiceForm>(emptyForm)
  const [deleteConfirm, setDeleteConfirm] = useState<number | null>(null)

  const setField = (key: keyof InvoiceForm, value: string) => {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  const startCreate = () => {
    setForm(emptyForm)
    setEditingId(null)
    setShowCreate(true)
  }

  const startEdit = (inv: ProviderInvoice) => {
    setForm({
      category_id: inv.category_id,
      invoice_number: inv.invoice_number,
      invoice_date: inv.invoice_date,
      amount: String(inv.amount),
      currency: inv.currency,
      assigned_month: inv.assigned_month ?? '',
    })
    setEditingId(inv.id)
    setShowCreate(true)
  }

  const handleSave = () => {
    if (editingId != null) {
      updateMutation.mutate(
        {
          id: editingId,
          data: {
            invoice_number: form.invoice_number,
            invoice_date: form.invoice_date,
            amount: parseFloat(form.amount),
            currency: form.currency,
            assigned_month: form.assigned_month || null,
          },
        },
        { onSuccess: () => { setShowCreate(false); setEditingId(null) } },
      )
    } else {
      createMutation.mutate(
        {
          category_id: form.category_id,
          invoice_number: form.invoice_number,
          invoice_date: form.invoice_date,
          amount: parseFloat(form.amount),
          currency: form.currency,
          assigned_month: form.assigned_month || null,
        },
        { onSuccess: () => { setShowCreate(false) } },
      )
    }
  }

  const handleDelete = () => {
    if (deleteConfirm != null) {
      deleteMutation.mutate(deleteConfirm, {
        onSuccess: () => setDeleteConfirm(null),
      })
    }
  }

  const handleUpload = (invoiceId: number, file: File) => {
    uploadMutation.mutate({ id: invoiceId, file })
  }

  return (
    <div>
      <PageHeader
        title="Lieferantenrechnungen"
        action={
          <button
            type="button"
            onClick={startCreate}
            className="rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
          >
            Neue Rechnung
          </button>
        }
      />

      {/* Create / Edit form */}
      {showCreate && (
        <div className="mb-6 rounded-lg border border-blue-200 bg-blue-50 p-5">
          <h3 className="mb-3 text-sm font-semibold text-gray-700">
            {editingId != null ? 'Rechnung bearbeiten' : 'Neue Lieferantenrechnung'}
          </h3>
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-3">
            {editingId == null && (
              <div>
                <label htmlFor="pi-category" className="block text-xs font-medium text-gray-600">Kategorie</label>
                <select
                  id="pi-category"
                  value={form.category_id}
                  onChange={(e) => setField('category_id', e.target.value)}
                  className="mt-1 w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm"
                >
                  <option value="">-- Kategorie --</option>
                  {categories?.map((c) => (
                    <option key={c.id} value={c.id}>{c.name}</option>
                  ))}
                </select>
              </div>
            )}
            <div>
              <label htmlFor="pi-number" className="block text-xs font-medium text-gray-600">Rechnungsnummer</label>
              <input
                id="pi-number"
                type="text"
                value={form.invoice_number}
                onChange={(e) => setField('invoice_number', e.target.value)}
                className="mt-1 w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm"
              />
            </div>
            <div>
              <label htmlFor="pi-date" className="block text-xs font-medium text-gray-600">Datum</label>
              <input
                id="pi-date"
                type="date"
                value={form.invoice_date}
                onChange={(e) => setField('invoice_date', e.target.value)}
                className="mt-1 w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm"
              />
            </div>
            <div>
              <label htmlFor="pi-amount" className="block text-xs font-medium text-gray-600">Betrag</label>
              <input
                id="pi-amount"
                type="number"
                step="0.01"
                value={form.amount}
                onChange={(e) => setField('amount', e.target.value)}
                className="mt-1 w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm"
              />
            </div>
            <div>
              <label htmlFor="pi-currency" className="block text-xs font-medium text-gray-600">Währung</label>
              <select
                id="pi-currency"
                value={form.currency}
                onChange={(e) => setField('currency', e.target.value)}
                className="mt-1 w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm"
              >
                <option value="EUR">EUR</option>
                <option value="USD">USD</option>
              </select>
            </div>
            <div>
              <label htmlFor="pi-month" className="block text-xs font-medium text-gray-600">Zugeordneter Monat</label>
              <input
                id="pi-month"
                type="month"
                value={form.assigned_month}
                onChange={(e) => setField('assigned_month', e.target.value)}
                className="mt-1 w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm"
              />
            </div>
          </div>
          <div className="mt-4 flex gap-3">
            <button
              type="button"
              onClick={handleSave}
              disabled={createMutation.isPending || updateMutation.isPending || !form.invoice_number || !form.amount}
              className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {(createMutation.isPending || updateMutation.isPending) ? 'Speichere...' : 'Speichern'}
            </button>
            <button
              type="button"
              onClick={() => { setShowCreate(false); setEditingId(null) }}
              className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Abbrechen
            </button>
            {(createMutation.isError || updateMutation.isError) && (
              <span className="text-sm text-red-600">
                Fehler: {(createMutation.error ?? updateMutation.error)?.message}
              </span>
            )}
          </div>
        </div>
      )}

      {/* Bulk upload */}
      <BulkUploadZone />

      {/* Filters */}
      <div className="mb-4 flex flex-wrap gap-3">
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
                <th className="px-4 py-3 text-left font-medium text-gray-600">Währung</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Zugeordnet</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Aktionen</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {invoices.map((inv) => (
                <tr key={inv.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium">{inv.invoice_number}</td>
                  <td className="px-4 py-3 text-gray-600">{inv.category_id}</td>
                  <td className="px-4 py-3 text-gray-600">{formatDateGerman(inv.invoice_date)}</td>
                  <td className="px-4 py-3 text-right"><AmountDisplay amount={inv.amount} currency={inv.currency} /></td>
                  <td className="px-4 py-3 text-gray-500">{inv.currency}</td>
                  <td className="px-4 py-3 text-gray-600">{inv.assigned_month ?? '-'}</td>
                  <td className="px-4 py-3">
                    <input
                      type="file"
                      accept=".pdf"
                      title="PDF hochladen"
                      ref={(el) => { fileInputRefs.current[inv.id] = el }}
                      onChange={(e) => {
                        const file = e.target.files?.[0]
                        if (file) handleUpload(inv.id, file)
                        e.target.value = ''
                      }}
                      className="hidden"
                    />
                    <div className="flex items-center gap-1.5">
                      {inv.file_path ? (
                        <>
                          <a
                            href={`/api/provider-invoices/${inv.id}/download`}
                            download
                            title="PDF herunterladen"
                            className="p-1 text-blue-600 hover:text-blue-800 cursor-pointer"
                          >
                            <Download size={16} />
                          </a>
                          <button
                            type="button"
                            title="Vorschau"
                            onClick={() => setPreviewInv({ id: inv.id, label: inv.invoice_number })}
                            className="p-1 text-gray-600 hover:text-gray-800 cursor-pointer"
                          >
                            <Eye size={16} />
                          </button>
                          <button
                            type="button"
                            title="PDF ersetzen"
                            onClick={() => fileInputRefs.current[inv.id]?.click()}
                            className="p-1 text-gray-500 hover:text-gray-700 cursor-pointer"
                          >
                            <RefreshCw size={16} />
                          </button>
                        </>
                      ) : (
                        <button
                          type="button"
                          title="PDF hochladen"
                          onClick={() => fileInputRefs.current[inv.id]?.click()}
                          className="p-1 text-blue-600 hover:text-blue-800 cursor-pointer"
                        >
                          <Upload size={16} />
                        </button>
                      )}
                      <span className="mx-0.5 border-l border-gray-200 self-stretch" />
                      <button
                        type="button"
                        title="Bearbeiten"
                        onClick={() => startEdit(inv)}
                        className="p-1 text-blue-600 hover:text-blue-800 cursor-pointer"
                      >
                        <Pencil size={16} />
                      </button>
                      <button
                        type="button"
                        title="Löschen"
                        onClick={() => setDeleteConfirm(inv.id)}
                        className="p-1 text-red-600 hover:text-red-800 cursor-pointer"
                      >
                        <Trash2 size={16} />
                      </button>
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
          url={`/api/provider-invoices/${previewInv.id}/download`}
          title={previewInv.label}
          onClose={() => setPreviewInv(null)}
        />
      )}

      <ConfirmDialog
        open={deleteConfirm != null}
        title="Lieferantenrechnung löschen"
        message="Möchten Sie diese Lieferantenrechnung wirklich löschen? Diese Aktion kann nicht rückgängig gemacht werden."
        onConfirm={handleDelete}
        onCancel={() => setDeleteConfirm(null)}
        confirmLabel="Löschen"
      />
    </div>
  )
}
