import type { InvoiceStatus } from '@/types/api'

/**
 * Format a number as German EUR: "1.234,56 EUR"
 * Mirrors backend/services/formatting.py:format_eur()
 */
export function formatEur(amount: number): string {
  const rounded = Math.round(amount * 100) / 100
  const fixed = Math.abs(rounded).toFixed(2)
  const [intPart, decPart] = fixed.split('.')
  // German thousands separator (period)
  const withSep = intPart!.replace(/\B(?=(\d{3})+(?!\d))/g, '.')
  const sign = rounded < 0 ? '-' : ''
  return `${sign}${withSep},${decPart} \u20AC`
}

/**
 * Format ISO date string as DD.MM.YYYY (German)
 */
export function formatDateGerman(isoDate: string): string {
  const [year, month, day] = isoDate.split('T')[0]!.split('-')
  return `${day}.${month}.${year}`
}

const MONTH_NAMES = [
  '', 'Januar', 'Februar', 'M\u00E4rz', 'April', 'Mai', 'Juni',
  'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember',
] as const

/** Format as "Januar 2025" */
export function formatMonthYear(year: number, month: number): string {
  return `${MONTH_NAMES[month]} ${year}`
}

/** Short month name "Jan", "Feb", etc. */
export function formatMonthShort(month: number): string {
  return (MONTH_NAMES[month] ?? '').slice(0, 3)
}

/** Generate invoice number: "202501-02" */
export function invoiceNumber(year: number, month: number, clientNumber: string): string {
  return `${year}${String(month).padStart(2, '0')}-${clientNumber}`
}

/** Today as ISO date string YYYY-MM-DD */
export function todayISO(): string {
  const d = new Date()
  const year = d.getFullYear()
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

/** Status label and Tailwind classes */
export const STATUS_CONFIG: Record<InvoiceStatus, { label: string; color: string }> = {
  draft:   { label: 'Entwurf',     color: 'bg-gray-100 text-gray-700' },
  sent:    { label: 'Versendet',   color: 'bg-blue-100 text-blue-700' },
  paid:    { label: 'Bezahlt',     color: 'bg-green-100 text-green-700' },
  overdue: { label: '\u00DCberf\u00E4llig', color: 'bg-red-100 text-red-700' },
}
