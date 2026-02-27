import { formatMonthYear } from '@/utils/format'

interface Props {
  year: number
  month: number
  onChange: (year: number, month: number) => void
}

export function MonthSelector({ year, month, onChange }: Props) {
  const goPrev = () => {
    if (month === 1) {
      onChange(year - 1, 12)
    } else {
      onChange(year, month - 1)
    }
  }

  const goNext = () => {
    if (month === 12) {
      onChange(year + 1, 1)
    } else {
      onChange(year, month + 1)
    }
  }

  return (
    <div className="flex items-center gap-3">
      <button
        onClick={goPrev}
        className="rounded-md border border-gray-300 px-2.5 py-1.5 text-sm hover:bg-gray-50"
        aria-label="Vorheriger Monat"
      >
        &larr;
      </button>

      <div className="flex items-center gap-2">
        <select
          value={month}
          onChange={(e) => onChange(year, Number(e.target.value))}
          className="rounded-md border border-gray-300 px-2 py-1.5 text-sm"
        >
          {Array.from({ length: 12 }, (_, i) => i + 1).map((m) => (
            <option key={m} value={m}>
              {formatMonthYear(year, m).split(' ')[0]}
            </option>
          ))}
        </select>

        <select
          value={year}
          onChange={(e) => onChange(Number(e.target.value), month)}
          className="rounded-md border border-gray-300 px-2 py-1.5 text-sm"
        >
          {Array.from({ length: 5 }, (_, i) => new Date().getFullYear() - 2 + i).map((y) => (
            <option key={y} value={y}>
              {y}
            </option>
          ))}
        </select>
      </div>

      <button
        onClick={goNext}
        className="rounded-md border border-gray-300 px-2.5 py-1.5 text-sm hover:bg-gray-50"
        aria-label="Nächster Monat"
      >
        &rarr;
      </button>

      <span className="text-sm font-medium text-gray-600">
        {formatMonthYear(year, month)}
      </span>
    </div>
  )
}
