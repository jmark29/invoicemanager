import { Link } from 'react-router-dom'

export function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center py-20">
      <h1 className="text-4xl font-bold text-gray-300">404</h1>
      <p className="mt-2 text-sm text-gray-500">Seite nicht gefunden</p>
      <Link
        to="/"
        className="mt-4 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
      >
        Zum Dashboard
      </Link>
    </div>
  )
}
