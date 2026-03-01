import { useRef, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { PageHeader } from '@/components/PageHeader'
import { AmountDisplay } from '@/components/AmountDisplay'
import { BulkUploadZone } from '@/components/BulkUploadZone'
import { useCostCategory, useProviderInvoices, useBankTransactions, useUploadProviderInvoicePdf, useUpdateCostCategory } from '@/hooks/useApi'
import { formatDateGerman, formatEur } from '@/utils/format'

export function CostCategoryDetail() {
  const { id } = useParams<{ id: string }>()
  const { data: category, isLoading } = useCostCategory(id ?? '')
  const { data: invoices } = useProviderInvoices({ category_id: id })
  const { data: bankTxns } = useBankTransactions({ category_id: id })
  const uploadMutation = useUploadProviderInvoicePdf()
  const updateMutation = useUpdateCostCategory()
  const fileInputRefs = useRef<Record<number, HTMLInputElement | null>>({})
  const [isEditing, setIsEditing] = useState(false)
  const [editForm, setEditForm] = useState<Record<string, string>>({})

  if (isLoading) return <p className="text-sm text-gray-500">Laden...</p>
  if (!category) return <p className="text-sm text-red-600">Kategorie nicht gefunden.</p>

  const startEditing = () => {
    setEditForm({
      name: category.name,
      provider_name: category.provider_name ?? '',
      provider_location: category.provider_location ?? '',
      billing_cycle: category.billing_cycle,
      cost_type: category.cost_type,
      currency: category.currency,
      vat_status: category.vat_status,
      bank_keywords: category.bank_keywords.join(', '),
      notes: category.notes ?? '',
      active: category.active ? 'true' : 'false',
    })
    setIsEditing(true)
  }

  const handleSave = () => {
    updateMutation.mutate(
      {
        id: category.id,
        data: {
          name: editForm.name || undefined,
          provider_name: editForm.provider_name || null,
          provider_location: editForm.provider_location || null,
          billing_cycle: editForm.billing_cycle || undefined,
          cost_type: editForm.cost_type || undefined,
          currency: editForm.currency || undefined,
          vat_status: editForm.vat_status || undefined,
          bank_keywords: editForm.bank_keywords
            ? editForm.bank_keywords.split(',').map((k) => k.trim()).filter(Boolean)
            : [],
          notes: editForm.notes || null,
          active: editForm.active === 'true',
        },
      },
      { onSuccess: () => setIsEditing(false) },
    )
  }

  const setField = (key: string, value: string) => {
    setEditForm((prev) => ({ ...prev, [key]: value }))
  }

  return (
    <div>
      <PageHeader
        title={category.name}
        action={
          <div className="flex gap-2">
            {!isEditing && (
              <button
                type="button"
                onClick={startEditing}
                className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
              >
                Bearbeiten
              </button>
            )}
            <Link
              to="/categories"
              className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Zurück
            </Link>
          </div>
        }
      />

      {/* Category details */}
      {isEditing ? (
        <div className="rounded-lg border border-blue-200 bg-blue-50 p-5">
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-3">
            <EditField label="Name" value={editForm.name ?? ''} onChange={(v) => setField('name', v)} />
            <EditField label="Anbieter" value={editForm.provider_name ?? ''} onChange={(v) => setField('provider_name', v)} />
            <EditField label="Standort" value={editForm.provider_location ?? ''} onChange={(v) => setField('provider_location', v)} />
            <EditField label="Kostentyp" value={editForm.cost_type ?? ''} onChange={(v) => setField('cost_type', v)} />
            <EditField label="Abrechnungszyklus" value={editForm.billing_cycle ?? ''} onChange={(v) => setField('billing_cycle', v)} />
            <EditField label="Währung" value={editForm.currency ?? ''} onChange={(v) => setField('currency', v)} />
            <EditField label="USt-Status" value={editForm.vat_status ?? ''} onChange={(v) => setField('vat_status', v)} />
            <EditField label="Bank-Schlüsselwörter (kommagetrennt)" value={editForm.bank_keywords ?? ''} onChange={(v) => setField('bank_keywords', v)} />
            <div>
              <label className="flex items-center gap-2 text-xs font-medium text-gray-600">
                <input
                  type="checkbox"
                  checked={editForm.active === 'true'}
                  onChange={(e) => setField('active', e.target.checked ? 'true' : 'false')}
                  className="h-4 w-4 rounded border-gray-300"
                />
                Aktiv
              </label>
            </div>
          </div>
          <div className="mt-3">
            <label htmlFor="cat-notes" className="block text-xs font-medium text-gray-600">Notizen</label>
            <textarea
              id="cat-notes"
              value={editForm.notes ?? ''}
              onChange={(e) => setField('notes', e.target.value)}
              rows={2}
              className="mt-1 w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm"
            />
          </div>
          <div className="mt-4 flex gap-3">
            <button
              type="button"
              onClick={handleSave}
              disabled={updateMutation.isPending}
              className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {updateMutation.isPending ? 'Speichere...' : 'Speichern'}
            </button>
            <button
              type="button"
              onClick={() => setIsEditing(false)}
              className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Abbrechen
            </button>
            {updateMutation.isError && (
              <span className="text-sm text-red-600">Fehler: {updateMutation.error.message}</span>
            )}
          </div>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-3">
            <Field label="ID" value={category.id} />
            <Field label="Anbieter" value={category.provider_name ?? '-'} />
            <Field label="Standort" value={category.provider_location ?? '-'} />
            <Field label="Kostentyp" value={category.cost_type} />
            <Field label="Abrechnungszyklus" value={category.billing_cycle} />
            <Field label="Währung" value={category.currency} />
            <Field label="USt-Status" value={category.vat_status} />
            <Field label="Verteilungsmethode" value={category.distribution_method ?? '-'} />
            <Field label="Sortierung" value={String(category.sort_order)} />
          </div>

          {/* Bank keywords */}
          <div className="mt-6">
            <h3 className="mb-2 text-sm font-semibold text-gray-700">Bank-Schlüsselwörter</h3>
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
        </>
      )}

      {/* Provider invoices */}
      <div className="mt-8">
        <h3 className="mb-3 text-sm font-semibold text-gray-700">
          Lieferantenrechnungen ({invoices?.length ?? 0})
        </h3>
        <BulkUploadZone categoryId={id} />
        {invoices && invoices.length > 0 ? (
          <div className="overflow-x-auto rounded-lg border border-gray-200">
            <table className="min-w-full divide-y divide-gray-200 bg-white text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 text-left font-medium text-gray-600">Nr.</th>
                  <th className="px-4 py-2 text-left font-medium text-gray-600">Datum</th>
                  <th className="px-4 py-2 text-right font-medium text-gray-600">Betrag</th>
                  <th className="px-4 py-2 text-left font-medium text-gray-600">Zugeordneter Monat</th>
                  <th className="px-4 py-2 text-left font-medium text-gray-600">PDF</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {invoices.map((inv) => (
                  <tr key={inv.id}>
                    <td className="px-4 py-2">{inv.invoice_number}</td>
                    <td className="px-4 py-2 text-gray-600">{formatDateGerman(inv.invoice_date)}</td>
                    <td className="px-4 py-2 text-right"><AmountDisplay amount={inv.amount} /></td>
                    <td className="px-4 py-2 text-gray-600">{inv.assigned_month ?? '-'}</td>
                    <td className="px-4 py-2">
                      <input
                        type="file"
                        accept=".pdf"
                        title="PDF hochladen"
                        ref={(el) => { fileInputRefs.current[inv.id] = el }}
                        onChange={(e) => {
                          const file = e.target.files?.[0]
                          if (file) uploadMutation.mutate({ id: inv.id, file })
                          e.target.value = ''
                        }}
                        className="hidden"
                      />
                      <div className="flex items-center gap-2">
                        {inv.file_path ? (
                          <>
                            <a
                              href={`/api/provider-invoices/${inv.id}/download`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-xs text-blue-600 hover:underline"
                            >
                              Download
                            </a>
                            <button
                              type="button"
                              onClick={() => fileInputRefs.current[inv.id]?.click()}
                              className="text-xs text-gray-500 hover:underline"
                            >
                              Ersetzen
                            </button>
                          </>
                        ) : (
                          <button
                            type="button"
                            onClick={() => fileInputRefs.current[inv.id]?.click()}
                            className="text-xs text-blue-600 hover:underline"
                          >
                            Hochladen
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-sm text-gray-400">Keine Lieferantenrechnungen.</p>
        )}
      </div>

      {/* Cost breakdown (for categories with matched FX data) */}
      {invoices && invoices.some((inv) => inv.amount_eur != null) && (
        <CostBreakdown invoices={invoices} currency={category.currency} />
      )}

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
                    <td className="px-4 py-2 text-gray-600 max-w-md truncate" title={tx.description}>{tx.description}</td>
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

function CostBreakdown({ invoices, currency }: { invoices: { invoice_number: string; amount: number; amount_eur: number | null; fx_rate: number | null; bank_fee: number | null; assigned_month: string | null }[]; currency: string }) {
  const matched = invoices.filter((inv) => inv.amount_eur != null)
  if (matched.length === 0) return null

  const totalOriginal = matched.reduce((sum, inv) => sum + inv.amount, 0)
  const totalEur = matched.reduce((sum, inv) => sum + (inv.amount_eur ?? 0), 0)
  const totalFee = matched.reduce((sum, inv) => sum + (inv.bank_fee ?? 0), 0)
  const avgFx = totalOriginal > 0 ? totalEur / totalOriginal : 0
  const isForeign = currency !== 'EUR'

  return (
    <div className="mt-8">
      <h3 className="mb-3 text-sm font-semibold text-gray-700">Kostenübersicht</h3>
      <div className="overflow-x-auto rounded-lg border border-gray-200">
        <table className="min-w-full divide-y divide-gray-200 bg-white text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-2 text-left font-medium text-gray-600">Rechnung</th>
              <th className="px-4 py-2 text-left font-medium text-gray-600">Monat</th>
              <th className="px-4 py-2 text-right font-medium text-gray-600">Betrag ({currency})</th>
              <th className="px-4 py-2 text-right font-medium text-gray-600">Bank (EUR)</th>
              {isForeign && <th className="px-4 py-2 text-right font-medium text-gray-600">FX-Kurs</th>}
              <th className="px-4 py-2 text-right font-medium text-gray-600">Bankgebühr</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {matched.map((inv) => (
              <tr key={inv.invoice_number} className="hover:bg-gray-50">
                <td className="px-4 py-2 font-medium">{inv.invoice_number}</td>
                <td className="px-4 py-2 text-gray-600">{inv.assigned_month ?? '-'}</td>
                <td className="px-4 py-2 text-right"><AmountDisplay amount={inv.amount} /></td>
                <td className="px-4 py-2 text-right"><AmountDisplay amount={inv.amount_eur ?? 0} /></td>
                {isForeign && (
                  <td className="px-4 py-2 text-right text-gray-500">
                    {inv.fx_rate != null ? inv.fx_rate.toFixed(4) : '-'}
                  </td>
                )}
                <td className="px-4 py-2 text-right text-gray-500">
                  {inv.bank_fee != null ? formatEur(inv.bank_fee) : '-'}
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot className="bg-gray-50 font-medium">
            <tr>
              <td className="px-4 py-2">Gesamt</td>
              <td className="px-4 py-2">{matched.length} Rechnungen</td>
              <td className="px-4 py-2 text-right"><AmountDisplay amount={totalOriginal} /></td>
              <td className="px-4 py-2 text-right"><AmountDisplay amount={totalEur} /></td>
              {isForeign && (
                <td className="px-4 py-2 text-right text-gray-500">
                  {avgFx > 0 ? `Ø ${avgFx.toFixed(4)}` : '-'}
                </td>
              )}
              <td className="px-4 py-2 text-right text-gray-500">{formatEur(totalFee)}</td>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  )
}

function EditField({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  const fieldId = `cat-${label.replace(/\s+/g, '-').toLowerCase()}`
  return (
    <div>
      <label htmlFor={fieldId} className="block text-xs font-medium text-gray-600">{label}</label>
      <input
        id={fieldId}
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm"
      />
    </div>
  )
}
