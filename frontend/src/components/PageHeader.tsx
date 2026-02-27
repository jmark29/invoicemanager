import type { ReactNode } from 'react'

interface Props {
  title: string
  action?: ReactNode
}

export function PageHeader({ title, action }: Props) {
  return (
    <div className="mb-6 flex items-center justify-between">
      <h1 className="text-2xl font-bold text-gray-900">{title}</h1>
      {action}
    </div>
  )
}
