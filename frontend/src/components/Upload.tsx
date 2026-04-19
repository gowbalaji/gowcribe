import { ChangeEvent, DragEvent, useRef, useState } from 'react'

interface Props {
  onStart: (jobId: string) => void
}

const FORMATS = ['mp3', 'mp4', 'm4a', 'wav', 'ogg', 'flac', 'webm', 'aac']
const MAX_MB = 600

function fmtSize(bytes: number) {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export default function Upload({ onStart }: Props) {
  const [file, setFile] = useState<File | null>(null)
  const [dragging, setDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  function validate(f: File): string {
    if (f.size > MAX_MB * 1024 * 1024) return `File exceeds ${MAX_MB} MB`
    const ext = f.name.split('.').pop()?.toLowerCase() ?? ''
    if (!FORMATS.includes(ext)) return `Unsupported format. Use: ${FORMATS.join(', ')}`
    return ''
  }

  function pick(f: File) {
    const err = validate(f)
    setError(err)
    setFile(err ? null : f)
  }

  function onDrop(e: DragEvent) {
    e.preventDefault()
    setDragging(false)
    const f = e.dataTransfer.files[0]
    if (f) pick(f)
  }

  function onInput(e: ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0]
    if (f) pick(f)
  }

  async function submit() {
    if (!file) return
    setUploading(true)
    setError('')
    try {
      const fd = new FormData()
      fd.append('file', file)
      const res = await fetch('/api/transcribe', {
        method: 'POST',
        body: fd,
        credentials: 'include',
      })
      if (!res.ok) {
        const d = await res.json().catch(() => ({}))
        throw new Error(d.detail ?? 'Upload failed')
      }
      const { job_id } = await res.json()
      onStart(job_id)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Upload failed')
      setUploading(false)
    }
  }

  return (
    <div className="section-wrap">
      <h2 className="section-title">Upload Audio</h2>
      <p className="section-sub">Up to 1 hour / 600 MB &nbsp;·&nbsp; Tamil (தமிழ்)</p>

      <div
        className={`drop-zone${dragging ? ' drag-over' : ''}${file ? ' has-file' : ''}`}
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => { if (!file) inputRef.current?.click() }}
      >
        <input
          ref={inputRef}
          type="file"
          accept={FORMATS.map(f => `.${f}`).join(',')}
          onChange={onInput}
          hidden
        />
        {file ? (
          <div className="file-info">
            <span className="file-icon">🎵</span>
            <div>
              <div className="file-name">{file.name}</div>
              <div className="file-size">{fmtSize(file.size)}</div>
            </div>
            <button
              className="btn-clear"
              onClick={(e) => { e.stopPropagation(); setFile(null); setError('') }}
              aria-label="Remove file"
            >✕</button>
          </div>
        ) : (
          <div className="drop-hint">
            <div className="drop-icon">↑</div>
            <div className="drop-text">
              Drop file here or <span className="link">browse</span>
            </div>
            <div className="drop-formats">{FORMATS.join(' · ')}</div>
          </div>
        )}
      </div>

      {error && <p className="error-msg">{error}</p>}

      <div className="language-badge">🇮🇳 Tamil — whisper-large-v3</div>

      <button
        className="btn-primary upload-btn"
        disabled={!file || uploading}
        onClick={submit}
      >
        {uploading ? 'Uploading…' : 'Transcribe'}
      </button>
    </div>
  )
}
