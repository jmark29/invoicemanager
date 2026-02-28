import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { StatusBadge } from '../StatusBadge'

describe('StatusBadge', () => {
  it('renders draft status in German', () => {
    render(<StatusBadge status="draft" />)
    expect(screen.getByText('Entwurf')).toBeInTheDocument()
  })

  it('renders sent status in German', () => {
    render(<StatusBadge status="sent" />)
    expect(screen.getByText('Versendet')).toBeInTheDocument()
  })

  it('renders paid status in German', () => {
    render(<StatusBadge status="paid" />)
    expect(screen.getByText('Bezahlt')).toBeInTheDocument()
  })

  it('renders overdue status in German', () => {
    render(<StatusBadge status="overdue" />)
    expect(screen.getByText('Überfällig')).toBeInTheDocument()
  })
})
