import { formatEur } from '@/utils/format'

interface Props {
  amount: number
  className?: string
  currency?: string
}

export function AmountDisplay({ amount, className = '', currency }: Props) {
  if (currency && currency !== 'EUR') {
    const rounded = Math.round(amount * 100) / 100
    const fixed = Math.abs(rounded).toFixed(2)
    const [intPart, decPart] = fixed.split('.')
    const withSep = intPart!.replace(/\B(?=(\d{3})+(?!\d))/g, '.')
    const sign = rounded < 0 ? '-' : ''
    const symbol = currency === 'USD' ? '$' : currency
    return <span className={className}>{sign}{withSep},{decPart} {symbol}</span>
  }
  return <span className={className}>{formatEur(amount)}</span>
}
