import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'

export default function NewConversationPage() {
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [expectations, setExpectations] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const conversation = await api.createConversation(name, expectations)
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
          <p className="muted">
            Name the practice scenario. Optionally say what kind of wording feedback you want so
            the editor can prefer specialized terms for that situation.
          </p>
        </div>
      </div>
      <form className="panel stack" onSubmit={onSubmit}>
        <label className="field">
          Conversation name
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Explaining a production outage to my team"
            required
          />
        </label>
        <label className="field">
          Feedback expectations (optional)
          <textarea
            value={expectations}
            onChange={(e) => setExpectations(e.target.value)}
            placeholder="e.g. Prefer SRE / incident vocabulary; stay calm and specific about blast radius, rollback, and customer impact."
            rows={4}
          />
        </label>
        <p className="muted">
          Leave blank for general precise English. Fill in when this chat needs domain words (legal,
          medical, product, academic, etc.).
        </p>
        {error && <p className="error">{error}</p>}
        <button type="submit" disabled={busy}>
          {busy ? 'Starting…' : 'Start'}
        </button>
      </form>
    </>
  )
}
