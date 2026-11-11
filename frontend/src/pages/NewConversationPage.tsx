import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'

type Preset = {
  label: string
  title: string
  feedback_expectations: string
  allow_idioms: boolean
}

const PRESETS: Preset[] = [
  {
    label: 'Reply to a client email',
    title: 'Reply to a client email',
    feedback_expectations: 'Formal and polite, clear commitments',
    allow_idioms: false,
  },
  {
    label: 'Team chat update',
    title: 'Team chat update',
    feedback_expectations: 'Neutral and brief',
    allow_idioms: true,
  },
  {
    label: 'Standup summary',
    title: 'Standup summary',
    feedback_expectations: 'Neutral, past and next steps',
    allow_idioms: true,
  },
  {
    label: 'Giving difficult feedback',
    title: 'Giving difficult feedback',
    feedback_expectations: 'Neutral, specific and kind',
    allow_idioms: false,
  },
  {
    label: 'Declining a request',
    title: 'Declining a request',
    feedback_expectations: 'Polite and firm',
    allow_idioms: false,
  },
  {
    label: 'Meeting summary',
    title: 'Meeting summary',
    feedback_expectations: 'Neutral, decisions and owners',
    allow_idioms: false,
  },
]

export default function NewConversationPage() {
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [expectations, setExpectations] = useState('')
  const [allowIdioms, setAllowIdioms] = useState(false)
  const [flowMode, setFlowMode] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  function applyPreset(preset: Preset) {
    setName(preset.title)
    setExpectations(preset.feedback_expectations)
    setAllowIdioms(preset.allow_idioms)
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const conversation = await api.createConversation(name, expectations, {
        flowMode,
        allowIdioms,
      })
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
            Pick a writing-task preset or name your own scenario. Optionally say what kind of
            wording feedback you want so the editor can prefer specialized terms.
          </p>
        </div>
      </div>
      <div className="panel stack">
        <p className="muted">Writing-task presets</p>
        <div className="preset-row">
          {PRESETS.map((preset) => (
            <button
              key={preset.label}
              type="button"
              className="ghost"
              onClick={() => applyPreset(preset)}
            >
              {preset.label}
            </button>
          ))}
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
        <label className="check">
          <input
            type="checkbox"
            checked={flowMode}
            onChange={(e) => setFlowMode(e.target.checked)}
          />
          Flow mode (write freely; wording feedback only in the recap at the end)
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
