import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, type Account } from '../api'

export default function AccountPage() {
  const [account, setAccount] = useState<Account | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    api
      .account()
      .then(setAccount)
      .catch((err: Error) => setError(err.message))
  }, [])

  async function onDelete() {
    const ok = window.confirm(
      'Delete your account and all data? This cannot be undone.',
    )
    if (!ok) return
    setBusy(true)
    setError(null)
    try {
      await api.deleteAccount()
      window.location.href = '/auth/logout'
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Delete failed')
      setBusy(false)
    }
  }

  const userLabel =
    account?.user.display_name || account?.user.email || account?.user.id || '…'
  const limits = account?.limits

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Account</h1>
          <p className="muted">Signed in as {userLabel}. Export or delete your data here.</p>
        </div>
      </div>

      {error && <p className="error">{error}</p>}

      <div className="panel stack">
        <h2 className="panel-title">Usage limits (24h)</h2>
        {limits ? (
          <ul className="plain-list">
            <li>
              LLM calls: {limits.llm_calls_24h} / {limits.llm_call_limit_per_day || '∞'}
            </li>
            <li>
              LLM cost: ${limits.llm_cost_usd_24h.toFixed(4)} / $
              {limits.llm_cost_limit_usd_per_day || '∞'}
            </li>
          </ul>
        ) : (
          <p className="muted">Loading limits…</p>
        )}
        <p className="muted">
          Login brute-force protection is enforced by authentik reputation policy. App LLM ceilings
          are enforced in vocab-coach.
        </p>
      </div>

      <div className="panel stack">
        <h2 className="panel-title">Privacy</h2>
        <p>{account?.privacy_note || 'Loading…'}</p>
        <p>
          <a href="/about/privacy">Full privacy notice</a>
        </p>
      </div>

      <div className="panel stack">
        <h2 className="panel-title">Your data</h2>
        <div className="cta-row">
          <a className="button-link" href="/api/account/export">
            Download my data (JSON)
          </a>
          <Link className="button-link secondary" to="/conversations">
            Back to conversations
          </Link>
        </div>
        <button type="button" className="ghost danger" disabled={busy} onClick={onDelete}>
          {busy ? 'Deleting…' : 'Delete my account'}
        </button>
      </div>
    </>
  )
}
