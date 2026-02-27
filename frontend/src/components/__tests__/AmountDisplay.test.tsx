import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { AmountDisplay } from '../AmountDisplay'

describe('AmountDisplay', () => {
  it('renders a formatted EUR amount', () => {
    render(<AmountDisplay amount={1234.56} />)
    expect(screen.getByText('1.234,56 \u20AC')).toBeInTheDocument()
  })

  it('renders zero amount', () => {
    render(<AmountDisplay amount={0} />)
    expect(screen.getByText('0,00 \u20AC')).toBeInTheDocument()
  })

  it('renders negative amount', () => {
    render(<AmountDisplay amount={-500} />)
    expect(screen.getByText('-500,00 \u20AC')).toBeInTheDocument()
  })

  it('applies custom className', () => {
    const { container } = render(<AmountDisplay amount={100} className="text-red-500" />)
    expect(container.querySelector('.text-red-500')).toBeInTheDocument()
  })
})
