import { useEffect, useState } from 'react'
import Download from './components/Download'
import Login from './components/Login'
import Transcribe from './components/Transcribe'
import Upload from './components/Upload'

type Screen = 'login' | 'upload' | 'transcribing' | 'done'

export default function App() {
  const [screen, setScreen] = useState<Screen>('login')
  const [email, setEmail] = useState('')
  const [jobId, setJobId] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/auth/me', { credentials: 'include' })
      .then(r => (r.ok ? r.json() : null))
      .then(data => {
        if (data?.email) {
          setEmail(data.email)
          setScreen('upload')
        }
      })
      .finally(() => setLoading(false))
  }, [])

  async function logout() {
    await fetch('/auth/logout', { method: 'POST', credentials: 'include' })
    setEmail('')
    setJobId('')
    setScreen('login')
  }

  if (loading) {
    return (
      <div className="loader-page">
        <div className="spinner" />
      </div>
    )
  }

  if (screen === 'login') return <Login />

  return (
    <div className="app">
      <header className="header">
        <span className="logo">Gowcribe</span>
        <div className="header-right">
          <span className="user-email">{email}</span>
          <button className="btn-ghost" onClick={logout}>Sign out</button>
        </div>
      </header>
      <main className="main">
        {screen === 'upload' && (
          <Upload onStart={(id) => { setJobId(id); setScreen('transcribing') }} />
        )}
        {screen === 'transcribing' && (
          <Transcribe jobId={jobId} onDone={() => setScreen('done')} />
        )}
        {screen === 'done' && (
          <Download jobId={jobId} onReset={() => { setJobId(''); setScreen('upload') }} />
        )}
      </main>
    </div>
  )
}
