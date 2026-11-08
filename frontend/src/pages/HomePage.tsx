import { Link } from 'react-router-dom'
import type { User } from '../api'

export default function HomePage({ user }: { user: User | null }) {
  const name = user?.display_name || user?.email || 'you'

  return (
    <section className="hero">
      <h1>vocab-coach</h1>
      <p>
        Signed in as {name}. Practise precise wording in conversation, then lock it in with drills and
        review.
      </p>
      <div className="cta-row">
        <Link className="button-link" to="/conversations/new">
          Start a conversation
        </Link>
        <Link className="button-link secondary" to="/drills">
          Do a rewrite drill
        </Link>
        <Link className="button-link ghost" to="/dashboard">
          See progress
        </Link>
      </div>
    </section>
  )
}
