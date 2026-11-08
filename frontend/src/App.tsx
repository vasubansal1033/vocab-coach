import { NavLink, Route, Routes } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { api, type User } from './api'
import HomePage from './pages/HomePage'
import ConversationsPage from './pages/ConversationsPage'
import NewConversationPage from './pages/NewConversationPage'
import ConversationPage from './pages/ConversationPage'
import DashboardPage from './pages/DashboardPage'
import LemmaPage from './pages/LemmaPage'
import ReviewPage from './pages/ReviewPage'
import DrillsPage from './pages/DrillsPage'

const links = [
  ['/', 'Home'],
  ['/conversations', 'Conversations'],
  ['/review', 'Review'],
  ['/drills', 'Drills'],
  ['/dashboard', 'Dashboard'],
] as const

export default function App() {
  const [user, setUser] = useState<User | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .me()
      .then(setUser)
      .catch((err: Error) => setError(err.message))
  }, [])

  return (
    <div className="app-shell">
      <header className="topbar">
        <NavLink to="/" className="brand">
          vocab-coach
        </NavLink>
        <nav className="nav">
          {links.map(([to, label]) => (
            <NavLink key={to} to={to} end={to === '/'} className={({ isActive }) => (isActive ? 'active' : undefined)}>
              {label}
            </NavLink>
          ))}
        </nav>
        <a className="muted" href="/account">
          Account
        </a>
        <a className="muted" href="/auth/logout">
          Log out
        </a>
      </header>

      {error && <p className="error">{error}</p>}

      <Routes>
        <Route path="/" element={<HomePage user={user} />} />
        <Route path="/conversations" element={<ConversationsPage />} />
        <Route path="/conversations/new" element={<NewConversationPage />} />
        <Route path="/conversations/:id" element={<ConversationPage />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/dashboard/lemma/:lemma" element={<LemmaPage />} />
        <Route path="/review" element={<ReviewPage />} />
        <Route path="/drills" element={<DrillsPage />} />
      </Routes>

      <p className="footer-note">
        Replace vague words with precise ones. <a href="/about/privacy">Privacy</a>
        {" · "}
        <a href="/about/attribution">Attribution</a>
      </p>
    </div>
  )
}
