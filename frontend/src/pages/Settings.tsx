import { useState, useEffect } from 'react'
import { PageHeader } from '@/components/PageHeader'
import { AmountDisplay } from '@/components/AmountDisplay'
import {
  useClients, useLineItemDefs, useUpdateLineItemDef,
  useCompanySettings, useUpdateCompanySettings,
} from '@/hooks/useApi'
import type { LineItemDefinition } from '@/types/api'

export function Settings() {
  return (
    <div>
      <PageHeader title="Einstellungen" />
      <CompanySettingsSection />
      <div className="mt-8">
        <LineItemSettings />
      </div>
    </div>
  )
}

// ── Company Settings ──────────────────────────────────────────

function CompanySettingsSection() {
  const { data: settings, isLoading } = useCompanySettings()
  const updateMutation = useUpdateCompanySettings()
  const [form, setForm] = useState<Record<string, string>>({})
  const [initialized, setInitialized] = useState(false)

  useEffect(() => {
    if (settings && !initialized) {
      setForm({
        company_name: settings.company_name ?? '',
        address_line1: settings.address_line1 ?? '',
        address_line2: settings.address_line2 ?? '',
        zip_city: settings.zip_city ?? '',
        managing_director: settings.managing_director ?? '',
        tax_number: settings.tax_number ?? '',
        vat_id: settings.vat_id ?? '',
        bank_name: settings.bank_name ?? '',
        iban: settings.iban ?? '',
        bic: settings.bic ?? '',
        email: settings.email ?? '',
        phone: settings.phone ?? '',
        fax: settings.fax ?? '',
        website: settings.website ?? '',
        register_info: settings.register_info ?? '',
      })
      setInitialized(true)
    }
  }, [settings, initialized])

  const setField = (key: string, value: string) => {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  const handleSave = () => {
    const data: Record<string, string | null> = {}
    for (const [key, value] of Object.entries(form)) {
      data[key] = value || null
    }
    updateMutation.mutate(data as Parameters<typeof updateMutation.mutate>[0])
  }

  if (isLoading) return <p className="text-sm text-gray-500">Laden...</p>

  const fields: { key: string; label: string }[] = [
    { key: 'company_name', label: 'Firmenname' },
    { key: 'address_line1', label: 'Adresse' },
    { key: 'address_line2', label: 'Adresse 2' },
    { key: 'zip_city', label: 'PLZ / Stadt' },
    { key: 'managing_director', label: 'Geschäftsführer' },
    { key: 'tax_number', label: 'Steuernummer' },
    { key: 'vat_id', label: 'USt-IdNr.' },
    { key: 'iban', label: 'IBAN' },
    { key: 'bic', label: 'BIC' },
    { key: 'bank_name', label: 'Bank' },
    { key: 'email', label: 'E-Mail' },
    { key: 'phone', label: 'Telefon' },
    { key: 'fax', label: 'Fax' },
    { key: 'website', label: 'Website' },
    { key: 'register_info', label: 'Handelsregister' },
  ]

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-5">
      <h2 className="mb-4 text-sm font-semibold text-gray-700">Unternehmensdaten</h2>
      <div className="grid grid-cols-2 gap-4">
        {fields.map(({ key, label }) => (
          <div key={key}>
            <label htmlFor={`company-${key}`} className="block text-xs font-medium text-gray-600">{label}</label>
            <input
              id={`company-${key}`}
              type="text"
              value={form[key] ?? ''}
              onChange={(e) => setField(key, e.target.value)}
              className="mt-1 w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm"
            />
          </div>
        ))}
      </div>
      <div className="mt-4">
        <button
          type="button"
          onClick={handleSave}
          disabled={updateMutation.isPending}
          className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {updateMutation.isPending ? 'Speichere...' : 'Speichern'}
        </button>
        {updateMutation.isSuccess && (
          <span className="ml-3 text-sm text-green-600">Gespeichert!</span>
        )}
      </div>
    </div>
  )
}

// ── Line Item Definitions ─────────────────────────────────────

function LineItemSettings() {
  const { data: clients } = useClients()
  const [selectedClientId, setSelectedClientId] = useState<string | undefined>(undefined)

  // Auto-select first client
  useEffect(() => {
    if (clients && clients.length > 0 && !selectedClientId) {
      const first = clients[0]
      if (first) setSelectedClientId(first.id)
    }
  }, [clients, selectedClientId])

  const { data: definitions, isLoading } = useLineItemDefs(selectedClientId)
  const updateMutation = useUpdateLineItemDef()

  const [editing, setEditing] = useState<number | null>(null)
  const [editLabel, setEditLabel] = useState('')
  const [editFixedAmount, setEditFixedAmount] = useState('')

  const startEdit = (def: LineItemDefinition) => {
    setEditing(def.id)
    setEditLabel(def.label)
    setEditFixedAmount(def.fixed_amount != null ? String(def.fixed_amount) : '')
  }

  const saveEdit = (defId: number) => {
    updateMutation.mutate({
      id: defId,
      data: {
        label: editLabel,
        fixed_amount: editFixedAmount ? parseFloat(editFixedAmount) : null,
      },
    })
    setEditing(null)
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-5">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-700">Rechnungspositionen</h2>
        {clients && clients.length > 1 && (
          <select
            value={selectedClientId ?? ''}
            onChange={(e) => setSelectedClientId(e.target.value || undefined)}
            title="Kunde auswählen"
            className="rounded-md border border-gray-300 px-3 py-1.5 text-sm"
          >
            {clients.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
        )}
      </div>
      {isLoading ? (
        <p className="text-sm text-gray-500">Laden...</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="px-3 py-2 text-left font-medium text-gray-600">Pos</th>
                <th className="px-3 py-2 text-left font-medium text-gray-600">Bezeichnung</th>
                <th className="px-3 py-2 text-left font-medium text-gray-600">Typ</th>
                <th className="px-3 py-2 text-left font-medium text-gray-600">Kategorie</th>
                <th className="px-3 py-2 text-right font-medium text-gray-600">Fester Betrag</th>
                <th className="px-3 py-2 text-left font-medium text-gray-600">Optional</th>
                <th className="px-3 py-2 text-left font-medium text-gray-600">Aktionen</th>
              </tr>
            </thead>
            <tbody>
              {definitions?.sort((a, b) => a.position - b.position).map((def) => (
                <tr key={def.id} className="border-b border-gray-100">
                  <td className="px-3 py-2">{def.position}</td>
                  <td className="px-3 py-2">
                    {editing === def.id ? (
                      <input
                        type="text"
                        value={editLabel}
                        onChange={(e) => setEditLabel(e.target.value)}
                        title="Bezeichnung"
                        className="w-full rounded border border-gray-300 px-2 py-0.5 text-sm"
                      />
                    ) : (
                      def.label
                    )}
                  </td>
                  <td className="px-3 py-2 text-gray-500">{def.source_type}</td>
                  <td className="px-3 py-2 text-gray-500">{def.category_id ?? '-'}</td>
                  <td className="px-3 py-2 text-right">
                    {editing === def.id ? (
                      <input
                        type="number"
                        step="0.01"
                        value={editFixedAmount}
                        onChange={(e) => setEditFixedAmount(e.target.value)}
                        title="Fester Betrag"
                        className="w-24 rounded border border-gray-300 px-2 py-0.5 text-right text-sm"
                      />
                    ) : (
                      def.fixed_amount != null ? <AmountDisplay amount={def.fixed_amount} /> : '-'
                    )}
                  </td>
                  <td className="px-3 py-2 text-gray-500">{def.is_optional ? 'Ja' : 'Nein'}</td>
                  <td className="px-3 py-2">
                    {editing === def.id ? (
                      <div className="flex gap-1">
                        <button type="button" onClick={() => saveEdit(def.id)} className="text-xs text-green-600 hover:underline">
                          Speichern
                        </button>
                        <button type="button" onClick={() => setEditing(null)} className="text-xs text-gray-500 hover:underline">
                          Abbrechen
                        </button>
                      </div>
                    ) : (
                      <button type="button" onClick={() => startEdit(def)} className="text-xs text-blue-600 hover:underline">
                        Bearbeiten
                      </button>
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
