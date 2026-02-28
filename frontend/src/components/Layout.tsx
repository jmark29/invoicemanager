import { NavLink, Outlet } from 'react-router-dom'
import { ErrorBoundary } from '@/components/ErrorBoundary'

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', icon: '⌂' },
  { to: '/invoices', label: 'Rechnungen', icon: '📄' },
  { to: '/invoices/generate', label: 'Rechnung erstellen', icon: '+' },
  { to: '/reconciliation', label: 'Abstimmung', icon: '⚖' },
  { to: '/clients', label: 'Kunden', icon: '👤' },
  { to: '/categories', label: 'Kategorien', icon: '☰' },
  { to: '/provider-invoices', label: 'Lieferantenrechnungen', icon: '📥' },
  { to: '/bank-transactions', label: 'Bank', icon: '🏦' },
  { to: '/upwork-transactions', label: 'Upwork', icon: '💻' },
  { to: '/payments', label: 'Zahlungen', icon: '€' },
  { to: '/settings', label: 'Einstellungen', icon: '⚙' },
] as const

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
              <span className="w-5 text-center">{item.icon}</span>
              {item.label}
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
