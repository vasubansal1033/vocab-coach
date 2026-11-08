import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, type Conversation } from '../api'

export default function ConversationsPage() {
  const [items, setItems] = useState<Conversation[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .conversations()
      .then((data) => setItems(data.conversations))
      .catch((err: Error) => setError(err.message))
  }, [])

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Conversations</h1>
          <p className="muted">Chat with the partner. The editor suggests sharper words after you write.</p>
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
              <li key={c.id}>
                <Link className="row" to={`/conversations/${c.id}`}>
                  <span>{c.title}</span>
                  <span className="muted">{c.created_at?.slice(0, 10)}</span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </>
  )
}
