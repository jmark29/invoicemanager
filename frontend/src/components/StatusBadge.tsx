import { STATUS_CONFIG } from '@/utils/format'
import type { InvoiceStatus } from '@/types/api'

interface Props {
  status: InvoiceStatus
}

export function StatusBadge({ status }: Props) {
  const config = STATUS_CONFIG[status]
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${config.color}`}>
      {config.label}
    </span>
  )
}
