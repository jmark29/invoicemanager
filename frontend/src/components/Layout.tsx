import { NavLink, Outlet } from 'react-router-dom'
import { ErrorBoundary } from '@/components/ErrorBoundary'

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', icon: '\u2302' },
  { to: '/invoices', label: 'Rechnungen', icon: '\uD83D\uDCC4' },
  { to: '/invoices/generate', label: 'Rechnung erstellen', icon: '\u002B' },
  { to: '/reconciliation', label: 'Abstimmung', icon: '\u2696' },
  { to: '/categories', label: 'Kategorien', icon: '\u2630' },
  { to: '/provider-invoices', label: 'Lieferantenrechnungen', icon: '\uD83D\uDCE5' },
  { to: '/bank-transactions', label: 'Bank', icon: '\uD83C\uDFE6' },
  { to: '/upwork-transactions', label: 'Upwork', icon: '\uD83D\uDCBB' },
  { to: '/payments', label: 'Zahlungen', icon: '\u20AC' },
  { to: '/settings', label: 'Einstellungen', icon: '\u2699' },
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
