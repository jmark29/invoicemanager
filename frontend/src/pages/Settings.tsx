import { useState, useEffect } from 'react'
import { PageHeader } from '@/components/PageHeader'
import { AmountDisplay } from '@/components/AmountDisplay'
import { Pencil } from 'lucide-react'
import {
  useClients, useLineItemDefs, useCreateLineItemDef, useUpdateLineItemDef,
  useCostCategories, useCompanySettings, useUpdateCompanySettings,
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

interface NewItemForm {
  position: string
  label: string
  source_type: string
  category_id: string
  fixed_amount: string
  is_optional: boolean
}

const emptyNewItem: NewItemForm = {
  position: '',
  label: '',
  source_type: 'fixed',
  category_id: '',
  fixed_amount: '',
  is_optional: false,
}

function LineItemSettings() {
  const { data: clients } = useClients()
  const { data: categories } = useCostCategories()
  const [selectedClientId, setSelectedClientId] = useState<string | undefined>(undefined)

  // Auto-select first client
  useEffect(() => {
    if (clients && clients.length > 0 && !selectedClientId) {
      const first = clients[0]
      if (first) setSelectedClientId(first.id)
    }
  }, [clients, selectedClientId])

  const { data: definitions, isLoading } = useLineItemDefs(selectedClientId)
  const createMutation = useCreateLineItemDef()
  const updateMutation = useUpdateLineItemDef()

  const [editing, setEditing] = useState<number | null>(null)
  const [editLabel, setEditLabel] = useState('')
  const [editFixedAmount, setEditFixedAmount] = useState('')

  const [showCreate, setShowCreate] = useState(false)
  const [newItem, setNewItem] = useState<NewItemForm>(emptyNewItem)

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

  const handleCreate = () => {
    if (!selectedClientId || !newItem.label || !newItem.position) return
    createMutation.mutate(
      {
        client_id: selectedClientId,
        position: parseInt(newItem.position, 10),
        label: newItem.label,
        source_type: newItem.source_type,
        category_id: newItem.category_id || null,
        fixed_amount: newItem.fixed_amount ? parseFloat(newItem.fixed_amount) : null,
        is_optional: newItem.is_optional,
      },
      { onSuccess: () => { setShowCreate(false); setNewItem(emptyNewItem) } },
    )
  }

  const nextPosition = definitions
    ? Math.max(...definitions.map((d) => d.position), 0) + 1
    : 1

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-5">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-700">Rechnungspositionen</h2>
        <div className="flex items-center gap-3">
          {clients && clients.length > 0 && (
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
          <button
            type="button"
            onClick={() => { setNewItem({ ...emptyNewItem, position: String(nextPosition) }); setShowCreate(true) }}
            className="rounded-md bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700"
          >
            Neue Position
          </button>
        </div>
      </div>

      {/* Inline creation form */}
      {showCreate && (
        <div className="mb-4 rounded-lg border border-blue-200 bg-blue-50 p-4">
          <h3 className="mb-3 text-xs font-semibold text-gray-700">Neue Rechnungsposition</h3>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <div>
              <label htmlFor="new-pos" className="block text-xs font-medium text-gray-600">Position</label>
              <input
                id="new-pos"
                type="number"
                value={newItem.position}
                onChange={(e) => setNewItem((prev) => ({ ...prev, position: e.target.value }))}
                className="mt-1 w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm"
              />
            </div>
            <div>
              <label htmlFor="new-label" className="block text-xs font-medium text-gray-600">Bezeichnung</label>
              <input
                id="new-label"
                type="text"
                value={newItem.label}
                onChange={(e) => setNewItem((prev) => ({ ...prev, label: e.target.value }))}
                className="mt-1 w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm"
              />
            </div>
            <div>
              <label htmlFor="new-source" className="block text-xs font-medium text-gray-600">Typ</label>
              <select
                id="new-source"
                value={newItem.source_type}
                onChange={(e) => setNewItem((prev) => ({ ...prev, source_type: e.target.value }))}
                className="mt-1 w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm"
              >
                <option value="fixed">fixed</option>
                <option value="category">category</option>
                <option value="manual">manual</option>
              </select>
            </div>
            <div>
              <label htmlFor="new-category" className="block text-xs font-medium text-gray-600">Kategorie</label>
              <select
                id="new-category"
                value={newItem.category_id}
                onChange={(e) => setNewItem((prev) => ({ ...prev, category_id: e.target.value }))}
                className="mt-1 w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm"
              >
                <option value="">-- keine --</option>
                {categories?.map((c) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="new-amount" className="block text-xs font-medium text-gray-600">Fester Betrag</label>
              <input
                id="new-amount"
                type="number"
                step="0.01"
                value={newItem.fixed_amount}
                onChange={(e) => setNewItem((prev) => ({ ...prev, fixed_amount: e.target.value }))}
                className="mt-1 w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm"
                placeholder="0.00"
              />
            </div>
            <div className="flex items-end">
              <label className="flex items-center gap-2 text-xs font-medium text-gray-600 pb-1.5">
                <input
                  type="checkbox"
                  checked={newItem.is_optional}
                  onChange={(e) => setNewItem((prev) => ({ ...prev, is_optional: e.target.checked }))}
                  className="h-4 w-4 rounded border-gray-300"
                />
                Optional
              </label>
            </div>
          </div>
          <div className="mt-3 flex gap-2">
            <button
              type="button"
              onClick={handleCreate}
              disabled={createMutation.isPending || !newItem.label || !newItem.position}
              className="rounded-md bg-blue-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {createMutation.isPending ? 'Erstelle...' : 'Erstellen'}
            </button>
            <button
              type="button"
              onClick={() => setShowCreate(false)}
              className="rounded-md border border-gray-300 bg-white px-4 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Abbrechen
            </button>
            {createMutation.isError && (
              <span className="text-sm text-red-600">Fehler: {createMutation.error.message}</span>
            )}
          </div>
        </div>
      )}

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
                      <button type="button" title="Bearbeiten" onClick={() => startEdit(def)} className="p-1 text-blue-600 hover:text-blue-800 cursor-pointer">
                        <Pencil size={16} />
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
