import { formatEur } from '@/utils/format'

interface Props {
  amount: number
  className?: string
}

export function AmountDisplay({ amount, className = '' }: Props) {
  return <span className={className}>{formatEur(amount)}</span>
}
