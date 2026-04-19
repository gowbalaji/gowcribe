import { useEffect, useState } from 'react'

interface Props {
  jobId: string
  onDone: () => void
}

interface Progress {
  status: 'queued' | 'splitting' | 'transcribing' | 'done' | 'error'
  percent: number
  message: string
}

export default function Transcribe({ jobId, onDone }: Props) {
  const [progress, setProgress] = useState<Progress>({
    status: 'queued',
    percent: 0,
    message: 'Preparing…',
  })

  useEffect(() => {
    const es = new EventSource(`/api/progress/${jobId}`, { withCredentials: true })

    es.onmessage = (e) => {
      const data: Progress = JSON.parse(e.data)
      setProgress(data)
      if (data.status === 'done') {
        es.close()
        setTimeout(onDone, 600)
      }
      if (data.status === 'error') {
        es.close()
      }
    }

    es.onerror = () => es.close()

    return () => es.close()
  }, [jobId, onDone])

  const isError = progress.status === 'error'

  return (
    <div className="section-wrap">
      <h2 className="section-title">
        {isError ? 'Transcription Failed' : 'Transcribing…'}
      </h2>
      <p className="section-sub">{progress.message}</p>

      <div className="progress-bar-wrap">
        <div
          className={`progress-bar-fill${isError ? ' is-error' : ''}`}
          style={{ width: `${progress.percent}%` }}
        />
      </div>
      <div className="progress-pct">{progress.percent}%</div>

      {!isError && (
        <p className="progress-note">
          Keep this tab open. A 1-hour file can take a few minutes.
        </p>
      )}
    </div>
  )
}
