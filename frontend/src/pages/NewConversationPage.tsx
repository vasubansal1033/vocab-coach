import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'

export default function NewConversationPage() {
  const navigate = useNavigate()
  const [topic, setTopic] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const conversation = await api.createConversation(topic)
      navigate(`/conversations/${conversation.id}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed')
      setBusy(false)
    }
  }

  return (
    <>
      <div className="page-head">
        <div>
          <h1>New conversation</h1>
          <p className="muted">Give the partner a topic or scenario to steer toward.</p>
        </div>
      </div>
      <form className="panel stack" onSubmit={onSubmit}>
        <label className="field">
          Topic or scenario
          <input
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="e.g. How last week's database migration went"
            required
          />
        </label>
        {error && <p className="error">{error}</p>}
        <button type="submit" disabled={busy}>
          {busy ? 'Starting…' : 'Start'}
        </button>
      </form>
    </>
  )
}
