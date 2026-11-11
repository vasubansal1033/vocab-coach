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
import AccountPage from './pages/AccountPage'

const links = [
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
      <header className="site-header">
        <div className="site-header-inner">
          <NavLink to="/" className="brand" end>
            vocab-coach
          </NavLink>
          <nav className="nav" aria-label="Main">
            {links.map(([to, label]) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) => (isActive ? 'active' : undefined)}
              >
                {label}
              </NavLink>
            ))}
          </nav>
          <div className="header-actions">
            <NavLink
              to="/account"
              className={({ isActive }) =>
                isActive ? 'header-link active' : 'header-link'
              }
            >
              {user?.display_name || user?.email || 'Account'}
            </NavLink>
            <a className="header-link" href="/auth/logout">
              Log out
            </a>
          </div>
        </div>
      </header>

      <main className="site-main">
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
          <Route path="/account" element={<AccountPage />} />
        </Routes>
      </main>

      <footer className="site-footer">
        <div className="site-footer-inner">
          <p className="footer-brand">vocab-coach</p>
          <p className="footer-tag">Replace vague words with precise ones.</p>
          <nav className="footer-nav" aria-label="Footer">
            <a href="/about/privacy">Privacy</a>
            <a href="/about/attribution">Attribution</a>
            <NavLink to="/account">Account</NavLink>
          </nav>
        </div>
      </footer>
    </div>
  )
}
