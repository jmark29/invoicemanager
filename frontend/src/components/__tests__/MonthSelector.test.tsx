import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MonthSelector } from '../MonthSelector'

describe('MonthSelector', () => {
  it('displays the current month and year', () => {
    const onChange = vi.fn()
    render(<MonthSelector year={2025} month={6} onChange={onChange} />)
    expect(screen.getByText('Juni 2025')).toBeInTheDocument()
  })

  it('calls onChange when clicking previous month button', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    render(<MonthSelector year={2025} month={6} onChange={onChange} />)

    await user.click(screen.getByLabelText('Vorheriger Monat'))
    expect(onChange).toHaveBeenCalledWith(2025, 5)
  })

  it('wraps to December when going before January', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    render(<MonthSelector year={2025} month={1} onChange={onChange} />)

    await user.click(screen.getByLabelText('Vorheriger Monat'))
    expect(onChange).toHaveBeenCalledWith(2024, 12)
  })

  it('calls onChange when clicking next month button', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    render(<MonthSelector year={2025} month={6} onChange={onChange} />)

    await user.click(screen.getByLabelText('Nächster Monat'))
    expect(onChange).toHaveBeenCalledWith(2025, 7)
  })

  it('wraps to January when going after December', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    render(<MonthSelector year={2025} month={12} onChange={onChange} />)

    await user.click(screen.getByLabelText('Nächster Monat'))
    expect(onChange).toHaveBeenCalledWith(2026, 1)
  })
})
