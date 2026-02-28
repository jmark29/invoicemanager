import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { PageHeader } from '@/components/PageHeader'
import { ErrorAlert } from '@/components/ErrorAlert'
import { useClients, useClient, useCreateClient, useUpdateClient } from '@/hooks/useApi'
import type { ClientCreate, ClientUpdate } from '@/types/api'

// ── Client List ───────────────────────────────────────────────

export function ClientList() {
  const navigate = useNavigate()
  const { data: clients, isLoading, isError, error, refetch } = useClients()

  return (
    <div>
      <PageHeader title="Kunden" action={
        <button
          type="button"
          onClick={() => navigate('/clients/new')}
          className="rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
        >
          Neuer Kunde
        </button>
      } />

      {isError ? (
        <ErrorAlert error={error} onRetry={() => void refetch()} />
      ) : isLoading ? (
        <p className="text-sm text-gray-500">Laden...</p>
      ) : !clients || clients.length === 0 ? (
        <div className="rounded-lg border border-gray-200 bg-white p-8 text-center text-sm text-gray-500">
          Keine Kunden vorhanden.
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-gray-200">
          <table className="min-w-full divide-y divide-gray-200 bg-white text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Name</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Kundennummer</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Stadt</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Ansprechpartner</th>
                <th className="px-4 py-3 text-center font-medium text-gray-600">Aktiv</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {clients.map((c) => (
                <tr
                  key={c.id}
                  onClick={() => navigate(`/clients/${c.id}`)}
                  className="cursor-pointer hover:bg-gray-50"
                >
                  <td className="px-4 py-3 font-medium">{c.name}</td>
                  <td className="px-4 py-3 text-gray-600">{c.client_number}</td>
                  <td className="px-4 py-3 text-gray-600">{c.zip_city}</td>
                  <td className="px-4 py-3 text-gray-600">{c.contact_person ?? '-'}</td>
                  <td className="px-4 py-3 text-center">
                    <span className={`inline-block h-2.5 w-2.5 rounded-full ${c.active ? 'bg-green-500' : 'bg-gray-300'}`} />
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

// ── Client Detail / Edit ──────────────────────────────────────

export function ClientDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const isNew = id === 'new'

  const { data: client, isLoading } = useClient(isNew ? '' : id!)
  const createMutation = useCreateClient()
  const updateMutation = useUpdateClient()

  const [form, setForm] = useState<Record<string, string | number | boolean | null>>({})
  const [initialized, setInitialized] = useState(false)

  // Initialize form from loaded client
  if (client && !initialized && !isNew) {
    setForm({
      client_number: client.client_number,
      name: client.name,
      address_line1: client.address_line1,
      address_line2: client.address_line2 ?? '',
      zip_city: client.zip_city,
      country: client.country ?? '',
      vat_id: client.vat_id ?? '',
      contact_person: client.contact_person ?? '',
      email: client.email ?? '',
      payment_terms_days: client.payment_terms_days ?? 14,
      notes: client.notes ?? '',
      vat_rate: client.vat_rate,
      active: client.active,
    })
    setInitialized(true)
  }

  // Initialize form for new client
  if (isNew && !initialized) {
    setForm({
      id: '',
      client_number: '',
      name: '',
      address_line1: '',
      address_line2: '',
      zip_city: '',
      country: 'Deutschland',
      vat_id: '',
      contact_person: '',
      email: '',
      payment_terms_days: 14,
      notes: '',
      vat_rate: 0.19,
      active: true,
    })
    setInitialized(true)
  }

  const setField = (key: string, value: string | number | boolean | null) => {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  const handleSave = async () => {
    if (isNew) {
      const data: ClientCreate = {
        id: String(form.id ?? ''),
        client_number: String(form.client_number ?? ''),
        name: String(form.name ?? ''),
        address_line1: String(form.address_line1 ?? ''),
        address_line2: form.address_line2 ? String(form.address_line2) : null,
        zip_city: String(form.zip_city ?? ''),
        country: form.country ? String(form.country) : null,
        vat_id: form.vat_id ? String(form.vat_id) : null,
        contact_person: form.contact_person ? String(form.contact_person) : null,
        email: form.email ? String(form.email) : null,
        payment_terms_days: form.payment_terms_days ? Number(form.payment_terms_days) : null,
        notes: form.notes ? String(form.notes) : null,
        vat_rate: Number(form.vat_rate ?? 0.19),
        active: Boolean(form.active),
      }
      await createMutation.mutateAsync(data)
      navigate(`/clients/${data.id}`)
    } else {
      const data: ClientUpdate = {
        client_number: String(form.client_number ?? ''),
        name: String(form.name ?? ''),
        address_line1: String(form.address_line1 ?? ''),
        address_line2: form.address_line2 ? String(form.address_line2) : null,
        zip_city: String(form.zip_city ?? ''),
        country: form.country ? String(form.country) : null,
        vat_id: form.vat_id ? String(form.vat_id) : null,
        contact_person: form.contact_person ? String(form.contact_person) : null,
        email: form.email ? String(form.email) : null,
        payment_terms_days: form.payment_terms_days ? Number(form.payment_terms_days) : null,
        notes: form.notes ? String(form.notes) : null,
        vat_rate: Number(form.vat_rate ?? 0.19),
        active: Boolean(form.active),
      }
      await updateMutation.mutateAsync({ id: id!, data })
    }
  }

  if (!isNew && isLoading) {
    return <p className="text-sm text-gray-500">Laden...</p>
  }

  return (
    <div>
      <PageHeader title={isNew ? 'Neuer Kunde' : (client?.name ?? 'Kunde')} action={
        <button
          type="button"
          onClick={() => navigate('/clients')}
          className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
        >
          Zurück
        </button>
      } />

      <div className="max-w-2xl space-y-4">
        {isNew && (
          <Field label="ID (Schlüssel)" value={String(form.id ?? '')} onChange={(v) => setField('id', v)} />
        )}
        <Field label="Kundennummer" value={String(form.client_number ?? '')} onChange={(v) => setField('client_number', v)} />
        <Field label="Name" value={String(form.name ?? '')} onChange={(v) => setField('name', v)} />
        <Field label="Adresszeile 1" value={String(form.address_line1 ?? '')} onChange={(v) => setField('address_line1', v)} />
        <Field label="Adresszeile 2" value={String(form.address_line2 ?? '')} onChange={(v) => setField('address_line2', v)} />
        <Field label="PLZ / Stadt" value={String(form.zip_city ?? '')} onChange={(v) => setField('zip_city', v)} />
        <Field label="Land" value={String(form.country ?? '')} onChange={(v) => setField('country', v)} />
        <Field label="USt-IdNr." value={String(form.vat_id ?? '')} onChange={(v) => setField('vat_id', v)} />
        <Field label="Ansprechpartner" value={String(form.contact_person ?? '')} onChange={(v) => setField('contact_person', v)} />
        <Field label="E-Mail" value={String(form.email ?? '')} onChange={(v) => setField('email', v)} />
        <Field label="Zahlungsziel (Tage)" value={String(form.payment_terms_days ?? '')} onChange={(v) => setField('payment_terms_days', v ? Number(v) : null)} type="number" />
        <Field label="USt-Satz" value={String(form.vat_rate ?? '')} onChange={(v) => setField('vat_rate', v ? Number(v) : 0.19)} type="number" step="0.01" />

        <div>
          <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
            <input
              type="checkbox"
              checked={Boolean(form.active)}
              onChange={(e) => setField('active', e.target.checked)}
              className="h-4 w-4 rounded border-gray-300"
            />
            Aktiv
          </label>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Notizen</label>
          <textarea
            value={String(form.notes ?? '')}
            onChange={(e) => setField('notes', e.target.value)}
            rows={3}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
          />
        </div>

        <div className="flex gap-3 pt-2">
          <button
            type="button"
            onClick={() => void handleSave()}
            disabled={createMutation.isPending || updateMutation.isPending}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            Speichern
          </button>
          <button
            type="button"
            onClick={() => navigate('/clients')}
            className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Abbrechen
          </button>
        </div>

        {(createMutation.isError || updateMutation.isError) && (
          <p className="text-sm text-red-600">
            Fehler: {(createMutation.error ?? updateMutation.error)?.message}
          </p>
        )}
      </div>
    </div>
  )
}

// ── Helper ────────────────────────────────────────────────────

function Field({
  label, value, onChange, type = 'text', step,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  type?: string
  step?: string
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
      <input
        type={type}
        step={step}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
      />
    </div>
  )
}
