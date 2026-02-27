interface Props {
  error: Error | null
  onRetry?: () => void
}

export function ErrorAlert({ error, onRetry }: Props) {
  if (!error) return null
  return (
    <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-center">
      <p className="text-sm font-medium text-red-700">Fehler beim Laden der Daten</p>
      <p className="mt-1 text-sm text-red-600">{error.message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-3 rounded-md bg-red-600 px-4 py-2 text-sm text-white hover:bg-red-700"
        >
          Erneut versuchen
        </button>
      )}
    </div>
  )
}
