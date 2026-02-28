import { useState, useRef, type DragEvent } from 'react'

interface Props {
  accept: string
  onFile: (file: File) => void
  label?: string
  disabled?: boolean
}

export function FileUpload({ accept, onFile, label = 'Datei auswählen oder hierher ziehen', disabled = false }: Props) {
  const [dragOver, setDragOver] = useState(false)
  const [fileName, setFileName] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleFile = (file: File) => {
    setFileName(file.name)
    onFile(file)
  }

  const handleDrop = (e: DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files[0]
    if (file) handleFile(file)
  }

  return (
    <div
      className={`rounded-lg border-2 border-dashed p-6 text-center transition-colors ${
        dragOver ? 'border-blue-400 bg-blue-50' : 'border-gray-300 bg-gray-50'
      } ${disabled ? 'cursor-not-allowed opacity-50' : 'cursor-pointer'}`}
      onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
      onClick={() => !disabled && inputRef.current?.click()}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0]
          if (file) handleFile(file)
        }}
        disabled={disabled}
      />
      {fileName ? (
        <p className="text-sm text-gray-700">{fileName}</p>
      ) : (
        <p className="text-sm text-gray-500">{label}</p>
      )}
    </div>
  )
}
