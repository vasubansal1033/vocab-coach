import { Link } from 'react-router-dom'
import type { User } from '../api'

export default function HomePage({ user }: { user: User | null }) {
  const name = user?.display_name || user?.email || 'you'

  return (
    <section className="hero">
      <p className="hero-eyebrow">Signed in as {name}</p>
      <h1>vocab-coach</h1>
      <p className="hero-lead">
        Practise precise wording in conversation, then lock it in with drills and review.
      </p>
      <div className="cta-row">
        <Link className="button-link" to="/conversations/new">
          Start a conversation
        </Link>
        <Link className="button-link secondary" to="/drills">
          Do a rewrite drill
        </Link>
      </div>
      <p className="hero-aside">
        <Link to="/dashboard">See your progress</Link>
      </p>
    </section>
  )
}
