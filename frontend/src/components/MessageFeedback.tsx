import { useEffect, useState } from 'react'
import { api, type FeedbackPayload, type Suggestion } from '../api'

type FeedbackState =
  | { status: 'loading' }
  | { status: 'failed' }
  | {
      status: 'ready'
      payload: FeedbackPayload
      done: Record<string, string>
    }

export default function MessageFeedback({
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
        else setState({ status: 'ready', payload: data, done: {} })
      })
      .catch(() => {
        if (!cancelled) setState({ status: 'failed' })
      })
    return () => {
      cancelled = true
    }
  }, [conversationId, messageId])

  async function accept(suggestion: Suggestion, optionId: string) {
    if (state.status !== 'ready') return
    try {
      const result = await api.accept(conversationId, suggestion.id, optionId)
      setState({
        ...state,
        done: {
          ...state.done,
          [suggestion.id]: `Accepted ${result.accepted_word} for ${result.original_text}`,
        },
      })
    } catch {
      setState({ status: 'failed' })
    }
  }

  async function dismiss(suggestion: Suggestion) {
    if (state.status !== 'ready') return
    try {
      const result = await api.dismiss(conversationId, suggestion.id)
      setState({
        ...state,
        done: {
          ...state.done,
          [suggestion.id]: `Dismissed: ${result.original_text}`,
        },
      })
    } catch {
      setState({ status: 'failed' })
    }
  }

  if (state.status === 'loading') {
    return (
      <aside className="feedback-panel" aria-busy="true" aria-label="Wording feedback">
        <h2 className="feedback-panel-title">Wording feedback</h2>
        <p className="muted">Checking wording across the message…</p>
      </aside>
    )
  }
  if (state.status === 'failed') {
    return (
      <aside className="feedback-panel" aria-label="Wording feedback">
        <h2 className="feedback-panel-title">Wording feedback</h2>
        <p className="muted">No feedback for this message</p>
      </aside>
    )
  }

  const { payload, done } = state
  const open = payload.suggestions.filter((s) => !done[s.id])

  return (
    <aside className="feedback-panel" aria-label="Wording feedback">
      <h2 className="feedback-panel-title">Wording feedback</h2>
      {payload.overview ? <p className="feedback-overview">{payload.overview}</p> : null}
      {payload.highlighted_html ? (
        <p
          className="highlighted"
          dangerouslySetInnerHTML={{ __html: payload.highlighted_html }}
        />
      ) : payload.content ? (
        <p className="highlighted">{payload.content}</p>
      ) : null}
      {!payload.suggestions.length ? (
        <p className="muted">No wording suggestions. The message already looks precise enough.</p>
      ) : null}
      {payload.suggestions.map((suggestion) =>
        done[suggestion.id] ? (
          <div className="suggestion done" key={suggestion.id}>
            <p>{done[suggestion.id]}</p>
          </div>
        ) : (
          <div className="suggestion" key={suggestion.id}>
            <p>
              <strong>{suggestion.original_text}</strong>
              {suggestion.why ? <span className="muted"> · {suggestion.why}</span> : null}
              {suggestion.question ? <em> · {suggestion.question}</em> : null}
            </p>
            <ul>
              {suggestion.options.map((opt) => (
                <li key={opt.id} className="option-row">
                  <button
                    type="button"
                    className="option"
                    onClick={() => accept(suggestion, opt.id)}
                  >
                    {opt.word}
                  </button>
                  <span className="muted">{opt.meaning}</span>
                </li>
              ))}
            </ul>
            <button type="button" className="ghost" onClick={() => dismiss(suggestion)}>
              Dismiss
            </button>
          </div>
        ),
      )}
      {payload.suggestions.length > 0 && open.length === 0 ? (
        <p className="muted">All suggestion spots handled for this message.</p>
      ) : null}
    </aside>
  )
}
