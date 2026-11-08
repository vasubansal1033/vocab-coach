import { useEffect, useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, type Message, type Suggestion } from '../api'

type FeedbackState =
  | { status: 'loading' }
  | { status: 'failed' }
  | { status: 'ready'; suggestions: Suggestion[] }
  | { status: 'resolved'; text: string }

function streamPartner(conversationId: string, messageId: string, onToken: (t: string) => void, onDone: (full: string) => void, onError: (msg: string) => void) {
  const source = new EventSource(
    `/api/conversations/${conversationId}/messages/${messageId}/partner`,
  )
  let full = ''
  source.addEventListener('token', (event) => {
    const data = (event as MessageEvent).data as string
    full += data
    onToken(data)
  })
  source.addEventListener('done', (event) => {
    const data = ((event as MessageEvent).data as string) || full
    source.close()
    onDone(data)
  })
  source.addEventListener('error', (event) => {
    const data = (event as MessageEvent).data as string | undefined
    source.close()
    onError(data || 'Partner stream failed')
  })
  source.onerror = () => {
    source.close()
  }
}

function Feedback({
  conversationId,
  messageId,
}: {
  conversationId: string
  messageId: string
}) {
  const [state, setState] = useState<FeedbackState>({ status: 'loading' })

  useEffect(() => {
    let cancelled = false
    api
      .feedback(conversationId, messageId)
      .then((data) => {
        if (cancelled) return
        if (data.failed) setState({ status: 'failed' })
        else setState({ status: 'ready', suggestions: data.suggestions })
      })
      .catch(() => {
        if (!cancelled) setState({ status: 'failed' })
      })
    return () => {
      cancelled = true
    }
  }, [conversationId, messageId])

  async function accept(suggestionId: string, optionId: string) {
    const result = await api.accept(conversationId, suggestionId, optionId)
    setState({
      status: 'resolved',
      text: `Accepted ${result.accepted_word} for ${result.original_text}`,
    })
  }

  async function dismiss(suggestionId: string) {
    const result = await api.dismiss(conversationId, suggestionId)
    setState({
      status: 'resolved',
      text: `Dismissed: ${result.original_text}`,
    })
  }

  if (state.status === 'loading') return <p className="muted">Checking wording…</p>
  if (state.status === 'failed') return <p className="muted">No feedback for this message</p>
  if (state.status === 'resolved') return <p>{state.text}</p>
  if (!state.suggestions.length) return <p className="muted">No wording suggestions.</p>

  return (
    <div className="feedback">
      {state.suggestions.map((suggestion) => (
        <div className="suggestion" key={suggestion.id}>
          <p>
            <strong>{suggestion.original_text}</strong>
            {suggestion.question ? <em> — {suggestion.question}</em> : null}
          </p>
          <ul>
            {suggestion.options.map((opt) => (
              <li key={opt.id} className="option-row">
                <button type="button" className="option" onClick={() => accept(suggestion.id, opt.id)}>
                  {opt.word}
                </button>
                <span className="muted">{opt.meaning}</span>
              </li>
            ))}
          </ul>
          <button type="button" className="ghost" onClick={() => dismiss(suggestion.id)}>
            Dismiss
          </button>
        </div>
      ))}
    </div>
  )
}

export default function ConversationPage() {
  const { id = '' } = useParams()
  const [title, setTitle] = useState('')
  const [messages, setMessages] = useState<Message[]>([])
  const [draft, setDraft] = useState('')
  const [busy, setBusy] = useState(false)
  const [partnerDraft, setPartnerDraft] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [pendingFeedbackId, setPendingFeedbackId] = useState<string | null>(null)

  useEffect(() => {
    api
      .conversation(id)
      .then((data) => {
        setTitle(data.title)
        setMessages(data.messages || [])
      })
      .catch((err: Error) => setError(err.message))
  }, [id])

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    if (!draft.trim() || busy) return
    setBusy(true)
    setError(null)
    setPartnerDraft('')
    try {
      const message = await api.postMessage(id, draft)
      setMessages((prev) => [...prev, message])
      setPendingFeedbackId(message.id)
      setDraft('')
      streamPartner(
        id,
        message.id,
        (token) => setPartnerDraft((prev) => (prev || '') + token),
        (full) => {
          setPartnerDraft(null)
          setMessages((prev) => [
            ...prev,
            {
              id: `partner-${message.id}`,
              role: 'partner',
              content: full,
              created_at: new Date().toISOString(),
            },
          ])
          setBusy(false)
        },
        (msg) => {
          setPartnerDraft(null)
          setError(msg)
          setBusy(false)
        },
      )
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed')
      setBusy(false)
      setPartnerDraft(null)
    }
  }

  return (
    <>
      <p>
        <Link to="/conversations">← All conversations</Link>
      </p>
      <div className="page-head">
        <h1>{title || 'Conversation'}</h1>
      </div>

      {error && <p className="error">{error}</p>}

      <div className="thread">
        {messages.map((message) => (
          <div key={message.id} className={`msg ${message.role}`}>
            <strong className="msg-role">{message.role === 'user' ? 'You' : 'Partner'}</strong>
            <p>{message.content}</p>
            {message.role === 'user' && pendingFeedbackId === message.id ? (
              <Feedback conversationId={id} messageId={message.id} />
            ) : null}
          </div>
        ))}
        {partnerDraft !== null ? (
          <div className="msg partner">
            <strong className="msg-role">Partner</strong>
            <p>{partnerDraft || '…'}</p>
          </div>
        ) : null}
      </div>

      <form className="panel stack" onSubmit={onSubmit}>
        <label className="field">
          Your message
          <textarea value={draft} onChange={(e) => setDraft(e.target.value)} required />
        </label>
        <button type="submit" disabled={busy}>
          {busy ? 'Sending…' : 'Send'}
        </button>
      </form>
    </>
  )
}
