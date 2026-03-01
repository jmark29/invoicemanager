import { useEffect, useState } from 'react'

interface PDFPreviewModalProps {
  url: string
  title: string
  onClose: () => void
}

export function PDFPreviewModal({ url, title, onClose }: PDFPreviewModalProps) {
  const [blobUrl, setBlobUrl] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let objectUrl: string | null = null
    setLoading(true)
    setError(null)
    setBlobUrl(null)

    fetch(url)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.blob()
      })
      .then((blob) => {
        objectUrl = URL.createObjectURL(blob)
        setBlobUrl(objectUrl)
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : 'Fehler beim Laden')
      })
      .finally(() => setLoading(false))

    return () => {
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [url])

  return (
    <div
      className="fixed inset-0 z-50 flex flex-col bg-black/60"
      onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
    >
      {/* Title bar */}
      <div className="flex items-center justify-between bg-gray-900 px-4 py-3 text-white">
        <span className="text-sm font-medium">{title}</span>
        <div className="flex items-center gap-3">
          <a
            href={url}
            download
            className="rounded bg-gray-700 px-3 py-1 text-xs hover:bg-gray-600"
          >
            Herunterladen
          </a>
          <button
            type="button"
            onClick={onClose}
            className="rounded bg-gray-700 px-3 py-1 text-xs hover:bg-gray-600"
          >
            Schließen
          </button>
        </div>
      </div>

      {/* PDF content area */}
      {loading && (
        <div className="flex flex-1 items-center justify-center bg-gray-100 text-sm text-gray-500">
          PDF wird geladen...
        </div>
      )}
      {error && (
        <div className="flex flex-1 items-center justify-center bg-gray-100 text-sm text-red-600">
          Fehler: {error}
        </div>
      )}
      {blobUrl && (
        <iframe
          src={blobUrl}
          title={title}
          className="flex-1 bg-white"
        />
      )}
    </div>
  )
}
