import { useState, useEffect } from 'react'
import { PageHeader } from '@/components/PageHeader'
import { useClients, useUpdateClient, useLineItemDefs, useUpdateLineItemDef } from '@/hooks/useApi'
import type { LineItemDefinition } from '@/types/api'

export function Settings() {
  const { data: clients } = useClients()
  const client = clients?.[0] // Typically only one client

  return (
    <div>
      <PageHeader title="Einstellungen" />

      {client && <ClientSettings clientId={client.id} />}

      <div className="mt-8">
        {client && <LineItemSettings clientId={client.id} />}
      </div>
    </div>
  )
}

function ClientSettings({ clientId }: { clientId: string }) {
  const { data: clients } = useClients()
  const client = clients?.find((c) => c.id === clientId)
  const updateMutation = useUpdateClient()

  const [name, setName] = useState('')
  const [clientNumber, setClientNumber] = useState('')
  const [address1, setAddress1] = useState('')
  const [address2, setAddress2] = useState('')
  const [zipCity, setZipCity] = useState('')
  const [vatRate, setVatRate] = useState('')

  useEffect(() => {
    if (client) {
      setName(client.name)
      setClientNumber(client.client_number)
      setAddress1(client.address_line1)
      setAddress2(client.address_line2 ?? '')
      setZipCity(client.zip_city)
      setVatRate(String(client.vat_rate))
    }
  }, [client])

  if (!client) return null

  const handleSave = () => {
    updateMutation.mutate({
      id: clientId,
      data: {
        name,
        client_number: clientNumber,
        address_line1: address1,
        address_line2: address2 || null,
        zip_city: zipCity,
        vat_rate: parseFloat(vatRate),
      },
    })
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-5">
      <h2 className="mb-4 text-sm font-semibold text-gray-700">Kundendaten</h2>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-xs font-medium text-gray-600">Name</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="mt-1 w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600">Kundennummer</label>
          <input
            type="text"
            value={clientNumber}
            onChange={(e) => setClientNumber(e.target.value)}
            className="mt-1 w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600">Adresse</label>
          <input
            type="text"
            value={address1}
            onChange={(e) => setAddress1(e.target.value)}
            className="mt-1 w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600">Adresse 2</label>
          <input
            type="text"
            value={address2}
            onChange={(e) => setAddress2(e.target.value)}
            className="mt-1 w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600">PLZ / Stadt</label>
          <input
            type="text"
            value={zipCity}
            onChange={(e) => setZipCity(e.target.value)}
            className="mt-1 w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600">USt-Satz</label>
          <input
            type="number"
            step="0.01"
            value={vatRate}
            onChange={(e) => setVatRate(e.target.value)}
            className="mt-1 w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm"
          />
        </div>
      </div>
      <div className="mt-4">
        <button
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

function LineItemSettings({ clientId }: { clientId: string }) {
  const { data: definitions, isLoading } = useLineItemDefs(clientId)
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

  if (isLoading) return <p className="text-sm text-gray-500">Laden...</p>

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-5">
      <h2 className="mb-4 text-sm font-semibold text-gray-700">Rechnungspositionen</h2>
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
                      className="w-24 rounded border border-gray-300 px-2 py-0.5 text-right text-sm"
                    />
                  ) : (
                    def.fixed_amount != null ? def.fixed_amount.toFixed(2) : '-'
                  )}
                </td>
                <td className="px-3 py-2 text-gray-500">{def.is_optional ? 'Ja' : 'Nein'}</td>
                <td className="px-3 py-2">
                  {editing === def.id ? (
                    <div className="flex gap-1">
                      <button onClick={() => saveEdit(def.id)} className="text-xs text-green-600 hover:underline">
                        Speichern
                      </button>
                      <button onClick={() => setEditing(null)} className="text-xs text-gray-500 hover:underline">
                        Abbrechen
                      </button>
                    </div>
                  ) : (
                    <button onClick={() => startEdit(def)} className="text-xs text-blue-600 hover:underline">
                      Bearbeiten
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
