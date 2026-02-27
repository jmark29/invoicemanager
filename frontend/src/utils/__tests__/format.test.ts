import { describe, it, expect } from 'vitest'
import {
  formatEur,
  formatDateGerman,
  formatMonthYear,
  formatMonthShort,
  invoiceNumber,
  todayISO,
  STATUS_CONFIG,
} from '../format'

describe('formatEur', () => {
  it('formats a positive amount with German separators', () => {
    expect(formatEur(1234.56)).toBe('1.234,56 \u20AC')
  })

  it('formats zero', () => {
    expect(formatEur(0)).toBe('0,00 \u20AC')
  })

  it('formats a negative amount', () => {
    expect(formatEur(-500.5)).toBe('-500,50 \u20AC')
  })

  it('formats a large amount matching invoice net total', () => {
    expect(formatEur(35535.8)).toBe('35.535,80 \u20AC')
  })

  it('formats an amount with no decimal part', () => {
    expect(formatEur(1000)).toBe('1.000,00 \u20AC')
  })

  it('rounds to 2 decimal places', () => {
    expect(formatEur(99.999)).toBe('100,00 \u20AC')
  })

  it('handles small amounts', () => {
    expect(formatEur(0.01)).toBe('0,01 \u20AC')
  })
})

describe('formatDateGerman', () => {
  it('formats ISO date as DD.MM.YYYY', () => {
    expect(formatDateGerman('2025-01-31')).toBe('31.01.2025')
  })

  it('handles date with time component', () => {
    expect(formatDateGerman('2025-06-15T12:00:00')).toBe('15.06.2025')
  })
})

describe('formatMonthYear', () => {
  it('formats January 2025', () => {
    expect(formatMonthYear(2025, 1)).toBe('Januar 2025')
  })

  it('formats March with umlaut', () => {
    expect(formatMonthYear(2025, 3)).toBe('M\u00E4rz 2025')
  })

  it('formats December', () => {
    expect(formatMonthYear(2025, 12)).toBe('Dezember 2025')
  })
})

describe('formatMonthShort', () => {
  it('returns 3-letter abbreviation', () => {
    expect(formatMonthShort(1)).toBe('Jan')
    expect(formatMonthShort(6)).toBe('Jun')
    expect(formatMonthShort(12)).toBe('Dez')
  })
})

describe('invoiceNumber', () => {
  it('generates correct invoice number format', () => {
    expect(invoiceNumber(2025, 1, '02')).toBe('202501-02')
  })

  it('pads single-digit months', () => {
    expect(invoiceNumber(2025, 6, '02')).toBe('202506-02')
  })

  it('handles double-digit months', () => {
    expect(invoiceNumber(2025, 12, '02')).toBe('202512-02')
  })
})

describe('todayISO', () => {
  it('returns a string in YYYY-MM-DD format', () => {
    const result = todayISO()
    expect(result).toMatch(/^\d{4}-\d{2}-\d{2}$/)
  })
})

describe('STATUS_CONFIG', () => {
  it('has German labels for all statuses', () => {
    expect(STATUS_CONFIG.draft.label).toBe('Entwurf')
    expect(STATUS_CONFIG.sent.label).toBe('Versendet')
    expect(STATUS_CONFIG.paid.label).toBe('Bezahlt')
    expect(STATUS_CONFIG.overdue.label).toBe('\u00DCberf\u00E4llig')
  })

  it('has color classes for all statuses', () => {
    for (const status of ['draft', 'sent', 'paid', 'overdue'] as const) {
      expect(STATUS_CONFIG[status].color).toBeTruthy()
    }
  })
})
