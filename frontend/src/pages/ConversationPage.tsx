import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api, type Message, type Recap } from '../api'
import MessageFeedback from '../components/MessageFeedback'

function openPartnerStream(
  conversationId: string,
  messageId: string,
  handlers: {
    onToken: (t: string) => void
    onDone: (full: string) => void
    onError: (msg: string) => void
  },
): EventSource {
  const source = new EventSource(
    `/api/conversations/${conversationId}/messages/${messageId}/partner`,
  )
  let full = ''
  let settled = false

  const settle = (fn: () => void) => {
    if (settled) return
    settled = true
    source.close()
    fn()
  }

  source.addEventListener('token', (event) => {
    const data = (event as MessageEvent).data as string
    full += data
    handlers.onToken(data)
  })
  source.addEventListener('done', (event) => {
    const data = ((event as MessageEvent).data as string) || full
    settle(() => handlers.onDone(data))
  })
  source.addEventListener('error', (event) => {
    const data = (event as MessageEvent).data as string | undefined
    settle(() => handlers.onError(data || 'Partner stream failed'))
  })
  source.onerror = () => {
    settle(() => handlers.onError('Partner stream disconnected'))
  }
  return source
}

export default function ConversationPage() {
  const { id = '' } = useParams()
  const navigate = useNavigate()
  const partnerSourceRef = useRef<EventSource | null>(null)
  const [title, setTitle] = useState('')
  const [expectations, setExpectations] = useState<string | null>(null)
  const [flowMode, setFlowMode] = useState(false)
  const [messages, setMessages] = useState<Message[]>([])
  const [feedbackIds, setFeedbackIds] = useState<Set<string>>(() => new Set())
  const [draft, setDraft] = useState('')
  const [busy, setBusy] = useState(false)
  const [partnerDraft, setPartnerDraft] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [recap, setRecap] = useState<Recap | null>(null)
  const [recapBusy, setRecapBusy] = useState(false)

  useEffect(() => {
    return () => {
      partnerSourceRef.current?.close()
      partnerSourceRef.current = null
    }
  }, [])

  useEffect(() => {
    api
      .conversation(id)
      .then((data) => {
        setTitle(data.title)
        setExpectations(data.feedback_expectations || null)
        const flow = Boolean(data.flow_mode)
        setFlowMode(flow)
        const msgs = data.messages || []
        setMessages(msgs)
        // Flow mode skips per-message feedback so suggestion_shown stays empty until recap.
        if (!flow) {
          setFeedbackIds(new Set(msgs.filter((m) => m.role === 'user').map((m) => m.id)))
        } else {
          setFeedbackIds(new Set())
        }
      })
      .catch((err: Error) => setError(err.message))
  }, [id])

  async function onDelete() {
    const ok = window.confirm(
      `Delete "${title || 'this conversation'}" permanently? Messages and feedback for it will be removed.`,
    )
    if (!ok) return
    setDeleting(true)
    try {
      await api.deleteConversation(id)
      navigate('/conversations')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Delete failed')
      setDeleting(false)
    }
  }

  async function onFinishRecap() {
    setRecapBusy(true)
    setError(null)
    try {
      const data = await api.recap(id)
      setRecap(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Recap failed')
    } finally {
      setRecapBusy(false)
    }
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    if (!draft.trim() || busy) return
    setBusy(true)
    setError(null)
    setPartnerDraft('')
    partnerSourceRef.current?.close()
    try {
      const message = await api.postMessage(id, draft)
      setMessages((prev) => [...prev, message])
      if (!flowMode) {
        setFeedbackIds((prev) => new Set(prev).add(message.id))
      }
      setDraft('')
      partnerSourceRef.current = openPartnerStream(id, message.id, {
        onToken: (token) => setPartnerDraft((prev) => (prev || '') + token),
        onDone: (full) => {
          partnerSourceRef.current = null
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
        onError: (msg) => {
          partnerSourceRef.current = null
          setPartnerDraft(null)
          setError(msg)
          setBusy(false)
        },
      })
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
        <div>
          <h1>{title || 'Conversation'}</h1>
          <p className="muted">
            {flowMode
              ? 'Flow mode: write freely. Finish to see wording feedback in the recap.'
              : 'Practice this scenario with the partner. Wording feedback appears in its own panel under your message.'}
          </p>
          {expectations ? (
            <p className="muted">
              <strong>Feedback focus:</strong> {expectations}
            </p>
          ) : null}
        </div>
        <button type="button" className="ghost danger" disabled={deleting} onClick={onDelete}>
          {deleting ? 'Deleting…' : 'Delete conversation'}
        </button>
      </div>

      {error && <p className="error">{error}</p>}

      <div className="thread">
        {messages.map((message) =>
          message.role === 'user' ? (
            <div className="turn" key={message.id}>
              <div className="msg user">
                <strong className="msg-role">You</strong>
                <p>{message.content}</p>
              </div>
              {feedbackIds.has(message.id) ? (
                <MessageFeedback
                  conversationId={id}
                  messageId={message.id}
                  onRetryText={setDraft}
                />
              ) : null}
            </div>
          ) : (
            <div key={message.id} className="msg partner">
              <strong className="msg-role">Partner</strong>
              <p>{message.content}</p>
            </div>
          ),
        )}
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
        <div className="row">
          <button type="submit" disabled={busy}>
            {busy ? 'Sending…' : 'Send'}
          </button>
          <button type="button" className="ghost" disabled={recapBusy} onClick={onFinishRecap}>
            {recapBusy ? 'Building recap…' : 'Finish and show recap'}
          </button>
        </div>
      </form>

      {recap ? (
        <aside className="panel stack" aria-label="Conversation recap">
          <h2>Recap</h2>
          <div>
            <h3>Words to keep</h3>
            {recap.words_to_keep.length ? (
              <ul>
                {recap.words_to_keep.map((w) => (
                  <li key={`${w.source}-${w.word}`}>
                    {w.word}
                    <span className="muted"> ({w.source})</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="muted">No keep words yet.</p>
            )}
          </div>
          <div>
            <h3>Crutch words</h3>
            {recap.crutch_words.length ? (
              <ul>
                {recap.crutch_words.map((c) => (
                  <li key={c.lemma}>
                    {c.lemma} × {c.count}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="muted">No crutch lemmas in this conversation.</p>
            )}
          </div>
          <div>
            <h3>One sentence to rewrite</h3>
            {recap.rewrite_sentence ? (
              <p>{recap.rewrite_sentence}</p>
            ) : (
              <p className="muted">No open suggestion left to practise.</p>
            )}
          </div>
        </aside>
      ) : null}
    </>
  )
}
