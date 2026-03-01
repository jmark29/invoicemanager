import { useState } from 'react'
import { MonthSelector } from '@/components/MonthSelector'
import { AmountDisplay } from '@/components/AmountDisplay'
import { PageHeader } from '@/components/PageHeader'
import { ErrorAlert } from '@/components/ErrorAlert'
import {
  useDashboardReconciliation,
  useConfirmMatch,
  useRejectMatch,
  useManualMatch,
  useProviderInvoices,
} from '@/hooks/useApi'
import { formatMonthYear, formatDateGerman, formatEur } from '@/utils/format'
import type { SuggestedMatch, CompletedMatch, UnmatchedBankTx } from '@/types/api'

export function Reconciliation() {
  const now = new Date()
  const [year, setYear] = useState(now.getFullYear())
  const [month, setMonth] = useState(now.getMonth() + 1)

  const { data, isLoading, isError, error, refetch } = useDashboardReconciliation(year, month)
  const confirmMatch = useConfirmMatch()
  const rejectMatch = useRejectMatch()
  const manualMatch = useManualMatch()

  // For manual match dialog
  const [manualMatchTx, setManualMatchTx] = useState<UnmatchedBankTx | null>(null)
  const [selectedInvoiceId, setSelectedInvoiceId] = useState<number | null>(null)
  const [bankFee, setBankFee] = useState('')

  const monthStr = `${year}-${String(month).padStart(2, '0')}`
  const { data: invoicesForMonth } = useProviderInvoices({ assigned_month: monthStr })

  const handleConfirm = (sm: SuggestedMatch) => {
    confirmMatch.mutate(
      { txId: sm.bank_transaction_id, invoiceId: sm.provider_invoice_id },
    )
  }

  const handleReject = (sm: SuggestedMatch) => {
    rejectMatch.mutate(sm.bank_transaction_id)
  }

  const handleManualMatchSubmit = () => {
    if (!manualMatchTx || !selectedInvoiceId) return
    manualMatch.mutate(
      {
        txId: manualMatchTx.id,
        invoiceId: selectedInvoiceId,
        bankFee: bankFee ? parseFloat(bankFee) : undefined,
      },
      { onSuccess: () => { setManualMatchTx(null); setSelectedInvoiceId(null); setBankFee('') } },
    )
  }

  return (
    <div>
      <PageHeader title="Abstimmung" />

      <MonthSelector
        year={year}
        month={month}
        onChange={(y, m) => { setYear(y); setMonth(m) }}
      />

      {isError && <ErrorAlert error={error} onRetry={() => void refetch()} />}

      {isLoading ? (
        <p className="mt-6 text-sm text-gray-500">Laden...</p>
      ) : data ? (
        <div className="mt-6 space-y-8">

          {/* ── Section 1: Monatsübersicht ── */}
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-5">
            <SummaryCard label="Rechnungen" value={data.provider_matches.length} />
            <SummaryCard
              label="Abgeglichen"
              value={data.matched_count}
              sub={`von ${data.matched_count + data.unmatched_count}`}
              color={data.matched_count > 0 ? 'green' : undefined}
            />
            <SummaryCard
              label="Vorgeschlagen"
              value={data.suggested_matches.length}
              color={data.suggested_matches.length > 0 ? 'blue' : undefined}
            />
            <SummaryCard
              label="Offen (Bank)"
              value={data.unmatched_bank_transactions.length}
              color={data.unmatched_bank_transactions.length > 0 ? 'amber' : undefined}
            />
            <SummaryCard
              label="Rechnungsstatus"
              value={data.invoice_status?.status ?? 'Keine Rechnung'}
              color={
                data.invoice_status
                  ? data.invoice_status.balance <= 0 ? 'green' : 'amber'
                  : undefined
              }
            />
          </div>

          {/* Invoice payment status bar */}
          {data.invoice_status && (
            <div className="rounded-lg border border-gray-200 bg-white p-5">
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                <div>
                  <p className="text-xs text-gray-500">Rechnung</p>
                  <p className="mt-1 font-medium">{data.invoice_status.invoice_number}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">Brutto</p>
                  <p className="mt-1 font-medium"><AmountDisplay amount={data.invoice_status.gross_total} /></p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">Bezahlt</p>
                  <p className="mt-1 font-medium"><AmountDisplay amount={data.invoice_status.total_paid} /></p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">Offen</p>
                  <p className={`mt-1 font-medium ${data.invoice_status.balance > 0 ? 'text-amber-600' : 'text-green-700'}`}>
                    <AmountDisplay amount={data.invoice_status.balance} />
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* ── Section 2: Offene Zuordnungen ── */}
          {(data.suggested_matches.length > 0 ||
            data.unmatched_bank_transactions.length > 0 ||
            data.unmatched_invoices.length > 0) && (
            <div className="space-y-6">
              <h2 className="text-sm font-semibold text-gray-700">
                Offene Zuordnungen
              </h2>

              {/* Suggested matches */}
              {data.suggested_matches.length > 0 && (
                <div>
                  <h3 className="mb-2 text-xs font-medium text-blue-700">
                    Vorgeschlagene Zuordnungen ({data.suggested_matches.length})
                  </h3>
                  <div className="space-y-3">
                    {data.suggested_matches.map((sm) => (
                      <SuggestedMatchCard
                        key={`${sm.bank_transaction_id}-${sm.provider_invoice_id}`}
                        match={sm}
                        onConfirm={() => handleConfirm(sm)}
                        onReject={() => handleReject(sm)}
                        isConfirming={confirmMatch.isPending}
                        isRejecting={rejectMatch.isPending}
                      />
                    ))}
                  </div>
                </div>
              )}

              {/* Unmatched bank transactions */}
              {data.unmatched_bank_transactions.length > 0 && (
                <div>
                  <h3 className="mb-2 text-xs font-medium text-amber-700">
                    Nicht zugeordnete Banktransaktionen ({data.unmatched_bank_transactions.length})
                  </h3>
                  <div className="overflow-x-auto rounded-lg border border-amber-200">
                    <table className="min-w-full divide-y divide-gray-200 bg-white text-sm">
                      <thead className="bg-amber-50">
                        <tr>
                          <th className="px-4 py-3 text-left font-medium text-gray-600">Buchungstag</th>
                          <th className="px-4 py-3 text-right font-medium text-gray-600">Betrag</th>
                          <th className="px-4 py-3 text-left font-medium text-gray-600">Beschreibung</th>
                          <th className="px-4 py-3 text-left font-medium text-gray-600">Kategorie</th>
                          <th className="px-4 py-3 text-center font-medium text-gray-600">Aktion</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {data.unmatched_bank_transactions.map((tx) => (
                          <tr key={tx.id} className="hover:bg-gray-50">
                            <td className="px-4 py-3 whitespace-nowrap">{formatDateGerman(tx.booking_date)}</td>
                            <td className="px-4 py-3 text-right whitespace-nowrap">
                              <AmountDisplay amount={tx.amount_eur} />
                            </td>
                            <td className="px-4 py-3 max-w-xs truncate" title={tx.description}>
                              {tx.description}
                            </td>
                            <td className="px-4 py-3 text-gray-500">{tx.category_id ?? '-'}</td>
                            <td className="px-4 py-3 text-center">
                              <button
                                type="button"
                                className="rounded bg-blue-50 px-2 py-1 text-xs font-medium text-blue-700 hover:bg-blue-100"
                                onClick={() => { setManualMatchTx(tx); setSelectedInvoiceId(null); setBankFee('') }}
                              >
                                Zuordnen
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Unmatched invoices */}
              {data.unmatched_invoices.length > 0 && (
                <div>
                  <h3 className="mb-2 text-xs font-medium text-amber-700">
                    Unbezahlte Rechnungen ({data.unmatched_invoices.length})
                  </h3>
                  <div className="overflow-x-auto rounded-lg border border-amber-200">
                    <table className="min-w-full divide-y divide-gray-200 bg-white text-sm">
                      <thead className="bg-amber-50">
                        <tr>
                          <th className="px-4 py-3 text-left font-medium text-gray-600">Rechnungsnr.</th>
                          <th className="px-4 py-3 text-left font-medium text-gray-600">Datum</th>
                          <th className="px-4 py-3 text-right font-medium text-gray-600">Betrag</th>
                          <th className="px-4 py-3 text-left font-medium text-gray-600">Währung</th>
                          <th className="px-4 py-3 text-left font-medium text-gray-600">Kategorie</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {data.unmatched_invoices.map((inv) => (
                          <tr key={inv.id} className="hover:bg-gray-50">
                            <td className="px-4 py-3 font-medium">{inv.invoice_number}</td>
                            <td className="px-4 py-3">{formatDateGerman(inv.invoice_date)}</td>
                            <td className="px-4 py-3 text-right">
                              <AmountDisplay amount={inv.amount} />
                            </td>
                            <td className="px-4 py-3">{inv.currency}</td>
                            <td className="px-4 py-3 text-gray-500">{inv.category_id}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ── Section 3: Abgeschlossene Zuordnungen ── */}
          {data.completed_matches.length > 0 && (
            <div>
              <h2 className="mb-3 text-sm font-semibold text-gray-700">
                Abgeschlossene Zuordnungen ({data.completed_matches.length})
              </h2>
              <div className="overflow-x-auto rounded-lg border border-gray-200">
                <table className="min-w-full divide-y divide-gray-200 bg-white text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left font-medium text-gray-600">Rechnung</th>
                      <th className="px-4 py-3 text-left font-medium text-gray-600">Kategorie</th>
                      <th className="px-4 py-3 text-right font-medium text-gray-600">Rechnungsbetrag</th>
                      <th className="px-4 py-3 text-left font-medium text-gray-600">Währung</th>
                      <th className="px-4 py-3 text-right font-medium text-gray-600">Bank EUR</th>
                      <th className="px-4 py-3 text-right font-medium text-gray-600">FX-Kurs</th>
                      <th className="px-4 py-3 text-right font-medium text-gray-600">Bankgebühr</th>
                      <th className="px-4 py-3 text-left font-medium text-gray-600">Buchungstag</th>
                      <th className="px-4 py-3 text-left font-medium text-gray-600">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {data.completed_matches.map((cm) => (
                      <CompletedMatchRow key={`${cm.bank_transaction_id}-${cm.provider_invoice_id}`} match={cm} />
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Legacy: provider matches table (invoices vs bank payments overview) */}
          <div>
            <h2 className="mb-3 text-sm font-semibold text-gray-700">
              Lieferantenrechnungen vs. Bankzahlungen — {formatMonthYear(year, month)}
            </h2>
            {data.provider_matches.length === 0 ? (
              <div className="rounded-lg border border-gray-200 bg-white p-6 text-center text-sm text-gray-500">
                Keine Lieferantenrechnungen für diesen Monat.
              </div>
            ) : (
              <div className="overflow-x-auto rounded-lg border border-gray-200">
                <table className="min-w-full divide-y divide-gray-200 bg-white text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left font-medium text-gray-600">Kategorie</th>
                      <th className="px-4 py-3 text-left font-medium text-gray-600">Rechnung</th>
                      <th className="px-4 py-3 text-right font-medium text-gray-600">Rechnungsbetrag</th>
                      <th className="px-4 py-3 text-center font-medium text-gray-600">Bankzahlung</th>
                      <th className="px-4 py-3 text-right font-medium text-gray-600">Bankbetrag</th>
                      <th className="px-4 py-3 text-left font-medium text-gray-600">Buchungsdatum</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {data.provider_matches.map((match, i) => (
                      <tr key={i} className={match.has_bank_payment ? 'hover:bg-gray-50' : 'bg-amber-50'}>
                        <td className="px-4 py-3 text-gray-700">{match.category_name}</td>
                        <td className="px-4 py-3 font-medium">{match.invoice_number}</td>
                        <td className="px-4 py-3 text-right">
                          <AmountDisplay amount={match.invoice_amount} />
                        </td>
                        <td className="px-4 py-3 text-center">
                          {match.has_bank_payment ? (
                            <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-green-100 text-green-700 text-xs">&#10003;</span>
                          ) : (
                            <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-red-100 text-red-700 text-xs">&#10007;</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-right">
                          {match.bank_amount != null ? <AmountDisplay amount={match.bank_amount} /> : '-'}
                        </td>
                        <td className="px-4 py-3 text-gray-600">
                          {match.bank_booking_date ? formatDateGerman(match.bank_booking_date) : '-'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="mt-6 rounded-lg border border-gray-200 bg-white p-8 text-center text-sm text-gray-500">
          Keine Daten für {formatMonthYear(year, month)}.
        </div>
      )}

      {/* Manual match dialog */}
      {manualMatchTx && (
        <ManualMatchDialog
          tx={manualMatchTx}
          invoices={invoicesForMonth ?? []}
          selectedInvoiceId={selectedInvoiceId}
          bankFee={bankFee}
          onSelectInvoice={setSelectedInvoiceId}
          onBankFeeChange={setBankFee}
          onSubmit={handleManualMatchSubmit}
          onCancel={() => setManualMatchTx(null)}
          isPending={manualMatch.isPending}
        />
      )}
    </div>
  )
}

// ── Sub-components ──────────────────────────────────────────

function SummaryCard({ label, value, sub, color }: {
  label: string
  value: string | number
  sub?: string
  color?: 'green' | 'blue' | 'amber'
}) {
  const colorClass = color === 'green' ? 'text-green-700'
    : color === 'blue' ? 'text-blue-700'
    : color === 'amber' ? 'text-amber-600'
    : 'text-gray-900'

  return (
    <div className="rounded-lg border border-gray-200 bg-white px-4 py-5">
      <p className="text-xs font-medium text-gray-500">{label}</p>
      <div className={`mt-1 text-lg font-semibold ${colorClass}`}>
        {value}
        {sub && <span className="ml-1 text-sm font-normal text-gray-400">{sub}</span>}
      </div>
    </div>
  )
}

function SuggestedMatchCard({ match, onConfirm, onReject, isConfirming, isRejecting }: {
  match: SuggestedMatch
  onConfirm: () => void
  onReject: () => void
  isConfirming: boolean
  isRejecting: boolean
}) {
  return (
    <div className="rounded-lg border border-blue-200 bg-blue-50 p-4">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 grid grid-cols-1 gap-3 sm:grid-cols-2">
          {/* Bank transaction side */}
          <div>
            <p className="text-xs font-medium text-gray-500 mb-1">Banktransaktion</p>
            <p className="text-sm font-medium">{formatDateGerman(match.tx_booking_date)}</p>
            <p className="text-sm"><AmountDisplay amount={match.tx_amount_eur} /> EUR</p>
            <p className="text-xs text-gray-500 truncate max-w-xs" title={match.tx_description}>
              {match.tx_description}
            </p>
          </div>
          {/* Invoice side */}
          <div>
            <p className="text-xs font-medium text-gray-500 mb-1">Lieferantenrechnung</p>
            <p className="text-sm font-medium">{match.inv_invoice_number}</p>
            <p className="text-sm"><AmountDisplay amount={match.inv_amount} /> {match.inv_currency}</p>
            <p className="text-xs text-gray-500">{match.inv_category_id}</p>
          </div>
        </div>
        <div className="flex flex-col items-end gap-2">
          <span className="rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700">
            {Math.round(match.confidence * 100)}%
          </span>
          <p className="text-xs text-gray-500">{match.match_reason}</p>
          <div className="flex gap-2">
            <button
              type="button"
              className="rounded bg-green-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-green-700 disabled:opacity-50"
              onClick={onConfirm}
              disabled={isConfirming || isRejecting}
            >
              Bestätigen
            </button>
            <button
              type="button"
              className="rounded bg-gray-200 px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-300 disabled:opacity-50"
              onClick={onReject}
              disabled={isConfirming || isRejecting}
            >
              Ablehnen
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

function CompletedMatchRow({ match }: { match: CompletedMatch }) {
  const hasFx = match.fx_rate != null && match.fx_rate !== 1.0

  return (
    <tr className="hover:bg-gray-50">
      <td className="px-4 py-3 font-medium">{match.inv_invoice_number}</td>
      <td className="px-4 py-3 text-gray-500">{match.inv_category_id}</td>
      <td className="px-4 py-3 text-right">
        <AmountDisplay amount={match.inv_amount} />
      </td>
      <td className="px-4 py-3">{match.inv_currency}</td>
      <td className="px-4 py-3 text-right">
        {match.amount_eur != null ? <AmountDisplay amount={match.amount_eur} /> : '-'}
      </td>
      <td className="px-4 py-3 text-right text-gray-500">
        {hasFx ? match.fx_rate!.toFixed(4) : '-'}
      </td>
      <td className="px-4 py-3 text-right text-gray-500">
        {match.bank_fee != null ? formatEur(match.bank_fee) : '-'}
      </td>
      <td className="px-4 py-3">{formatDateGerman(match.tx_booking_date)}</td>
      <td className="px-4 py-3">
        <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
          match.match_status === 'auto_matched' ? 'bg-green-100 text-green-700' :
          match.match_status === 'manual' ? 'bg-blue-100 text-blue-700' :
          'bg-gray-100 text-gray-700'
        }`}>
          {match.match_status === 'auto_matched' ? 'Auto' :
           match.match_status === 'manual' ? 'Manuell' :
           match.match_status}
        </span>
      </td>
    </tr>
  )
}

function ManualMatchDialog({ tx, invoices, selectedInvoiceId, bankFee, onSelectInvoice, onBankFeeChange, onSubmit, onCancel, isPending }: {
  tx: UnmatchedBankTx
  invoices: { id: number; invoice_number: string; amount: number; currency: string; category_id: string }[]
  selectedInvoiceId: number | null
  bankFee: string
  onSelectInvoice: (id: number | null) => void
  onBankFeeChange: (v: string) => void
  onSubmit: () => void
  onCancel: () => void
  isPending: boolean
}) {
  // Filter to unmatched invoices where category matches if possible
  const candidates = invoices.filter((inv) =>
    !tx.category_id || inv.category_id === tx.category_id
  )
  const otherInvoices = invoices.filter((inv) =>
    tx.category_id && inv.category_id !== tx.category_id
  )

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-lg rounded-lg bg-white p-6 shadow-xl">
        <h3 className="text-base font-semibold text-gray-900 mb-4">Manuell zuordnen</h3>

        <div className="mb-4 rounded-lg bg-gray-50 p-3 text-sm">
          <p className="font-medium">Banktransaktion #{tx.id}</p>
          <p>{formatDateGerman(tx.booking_date)} — <AmountDisplay amount={tx.amount_eur} /> EUR</p>
          <p className="text-xs text-gray-500 truncate">{tx.description}</p>
        </div>

        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-1">Rechnung auswählen</label>
          <select
            aria-label="Rechnung auswählen"
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            value={selectedInvoiceId ?? ''}
            onChange={(e) => onSelectInvoice(e.target.value ? Number(e.target.value) : null)}
          >
            <option value="">Bitte wählen...</option>
            {candidates.length > 0 && (
              <optgroup label="Passende Kategorie">
                {candidates.map((inv) => (
                  <option key={inv.id} value={inv.id}>
                    {inv.invoice_number} — {formatEur(inv.amount)} {inv.currency} ({inv.category_id})
                  </option>
                ))}
              </optgroup>
            )}
            {otherInvoices.length > 0 && (
              <optgroup label="Andere Kategorien">
                {otherInvoices.map((inv) => (
                  <option key={inv.id} value={inv.id}>
                    {inv.invoice_number} — {formatEur(inv.amount)} {inv.currency} ({inv.category_id})
                  </option>
                ))}
              </optgroup>
            )}
          </select>
        </div>

        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Bankgebühr (EUR, optional)
          </label>
          <input
            type="number"
            step="0.01"
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            value={bankFee}
            onChange={(e) => onBankFeeChange(e.target.value)}
            placeholder="0.00"
          />
        </div>

        <div className="flex justify-end gap-3">
          <button
            type="button"
            className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            onClick={onCancel}
          >
            Abbrechen
          </button>
          <button
            type="button"
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            onClick={onSubmit}
            disabled={!selectedInvoiceId || isPending}
          >
            {isPending ? 'Wird zugeordnet...' : 'Zuordnen'}
          </button>
        </div>
      </div>
    </div>
  )
}
