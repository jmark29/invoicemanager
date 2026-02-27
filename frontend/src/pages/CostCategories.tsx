import { useNavigate } from 'react-router-dom'
import { PageHeader } from '@/components/PageHeader'
import { DataTable, type Column } from '@/components/DataTable'
import { ErrorAlert } from '@/components/ErrorAlert'
import { useCostCategories } from '@/hooks/useApi'
import type { CostCategory } from '@/types/api'

const columns: Column<CostCategory>[] = [
  { key: 'id', header: 'ID' },
  { key: 'name', header: 'Name' },
  { key: 'provider_name', header: 'Anbieter', render: (r) => r.provider_name ?? '-' },
  { key: 'cost_type', header: 'Kostentyp' },
  { key: 'billing_cycle', header: 'Abrechnungszyklus' },
  { key: 'currency', header: 'W\u00E4hrung' },
  {
    key: 'active',
    header: 'Aktiv',
    render: (r) => (
      <span className={`inline-block h-2 w-2 rounded-full ${r.active ? 'bg-green-500' : 'bg-gray-300'}`} />
    ),
  },
]

export function CostCategories() {
  const navigate = useNavigate()
  const { data: categories, isLoading, isError, error, refetch } = useCostCategories()

  if (isLoading) return <p className="text-sm text-gray-500">Laden...</p>
  if (isError) return <ErrorAlert error={error} onRetry={() => void refetch()} />

  return (
    <div>
      <PageHeader title="Kostenkategorien" />
      <DataTable
        columns={columns}
        data={categories ?? []}
        keyFn={(r) => r.id}
        onRowClick={(r) => navigate(`/categories/${r.id}`)}
        emptyMessage="Keine Kategorien vorhanden."
      />
    </div>
  )
}
