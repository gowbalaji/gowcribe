interface Props {
  jobId: string
  onReset: () => void
}

export default function Download({ jobId, onReset }: Props) {
  function download(fmt: 'txt' | 'srt') {
    window.location.href = `/api/download/${jobId}?fmt=${fmt}`
  }

  return (
    <div className="section-wrap download-wrap">
      <div className="success-icon" aria-hidden="true">✓</div>
      <h2 className="section-title">Transcription Ready</h2>
      <p className="section-sub">Your audio has been transcribed in Tamil</p>

      <div className="download-btns">
        <button className="btn-primary" onClick={() => download('txt')}>
          Download .txt
        </button>
        <button className="btn-secondary" onClick={() => download('srt')}>
          Download .srt &nbsp;<span style={{ color: 'var(--grey-400)', fontSize: 12 }}>subtitles</span>
        </button>
      </div>

      <button className="btn-ghost" onClick={onReset} style={{ marginTop: 16 }}>
        ← Transcribe another file
      </button>
    </div>
  )
}
