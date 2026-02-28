interface PDFPreviewModalProps {
  url: string
  title: string
  onClose: () => void
}

export function PDFPreviewModal({ url, title, onClose }: PDFPreviewModalProps) {
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
            target="_blank"
            rel="noopener noreferrer"
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

      {/* PDF iframe */}
      <iframe
        src={url}
        title={title}
        className="flex-1 bg-white"
      />
    </div>
  )
}
