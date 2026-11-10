import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, type Conversation } from '../api'

export default function ConversationsPage() {
  const [items, setItems] = useState<Conversation[]>([])
  const [error, setError] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  useEffect(() => {
    api
      .conversations()
      .then((data) => setItems(data.conversations))
      .catch((err: Error) => setError(err.message))
  }, [])

  async function onDelete(conversation: Conversation) {
    const ok = window.confirm(
      `Delete "${conversation.title}" permanently? Messages and feedback for it will be removed.`,
    )
    if (!ok) return
    setDeletingId(conversation.id)
    setError(null)
    try {
      await api.deleteConversation(conversation.id)
      setItems((prev) => prev.filter((c) => c.id !== conversation.id))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Delete failed')
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Conversations</h1>
          <p className="muted">
            Pick a practice scenario, chat with the partner, then get wording feedback tuned to that
            conversation’s expectations.
          </p>
        </div>
        <Link className="button-link" to="/conversations/new">
          New conversation
        </Link>
      </div>

      {error && <p className="error">{error}</p>}

      <div className="panel">
        {!items.length ? (
          <p className="muted">No conversations yet.</p>
        ) : (
          <ul className="list">
            {items.map((c) => (
              <li key={c.id} className="conversation-row">
                <Link className="row" to={`/conversations/${c.id}`}>
                  <span>
                    {c.title}
                    {c.feedback_expectations ? (
                      <span className="muted row-sub">Has feedback focus</span>
                    ) : null}
                  </span>
                  <span className="muted">{c.created_at?.slice(0, 10)}</span>
                </Link>
                <button
                  type="button"
                  className="ghost danger"
                  disabled={deletingId === c.id}
                  onClick={() => onDelete(c)}
                >
                  {deletingId === c.id ? 'Deleting…' : 'Delete'}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </>
  )
}
