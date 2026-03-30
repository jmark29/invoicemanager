import { NavLink, Outlet } from 'react-router-dom'
import { ErrorBoundary } from '@/components/ErrorBoundary'
import {
  LayoutDashboard, FileText, FilePlus, Scale, BarChart3, Users,
  LayoutList, FileDown, Landmark, Monitor, Euro, Settings,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

const NAV_ITEMS: { to: string; label: string; icon: LucideIcon }[] = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/invoices', label: 'Rechnungen', icon: FileText },
  { to: '/invoices/generate', label: 'Rechnung erstellen', icon: FilePlus },
  { to: '/reconciliation', label: 'Abstimmung', icon: Scale },
  { to: '/cost-reconciliation', label: 'Kostenabgleich', icon: BarChart3 },
  { to: '/clients', label: 'Kunden', icon: Users },
  { to: '/categories', label: 'Kategorien', icon: LayoutList },
  { to: '/provider-invoices', label: 'Lieferantenrechnungen', icon: FileDown },
  { to: '/bank-transactions', label: 'Bank', icon: Landmark },
  { to: '/upwork-transactions', label: 'Upwork', icon: Monitor },
  { to: '/payments', label: 'Zahlungen', icon: Euro },
  { to: '/settings', label: 'Einstellungen', icon: Settings },
]

export function Layout() {
  return (
    <div className="flex h-screen">
      {/* Sidebar */}
      <aside className="flex w-64 flex-col bg-gray-900 text-gray-300">
        <div className="border-b border-gray-700 px-5 py-4">
          <h1 className="text-lg font-bold text-white">Invoice Manager</h1>
        </div>
        <nav className="flex-1 overflow-y-auto py-3">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 px-5 py-2.5 text-sm transition-colors ${
                  isActive
                    ? 'bg-gray-800 text-white font-medium'
                    : 'hover:bg-gray-800 hover:text-white'
                }`
              }
            >
              {({ isActive }) => (
                <>
                  <item.icon
                    size={18}
                    className={`w-5 h-5 flex-shrink-0 ${isActive ? 'text-white' : 'text-gray-400'}`}
                  />
                  <span>{item.label}</span>
                </>
              )}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-gray-700 px-5 py-3 text-xs text-gray-500">
          29ventures GmbH
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto bg-gray-50 p-6">
        <ErrorBoundary>
          <Outlet />
        </ErrorBoundary>
      </main>
    </div>
  )
}
