import { useEffect, useState, type FormEvent } from 'react'
import { api } from '../api'

type Drill = { id: string; vague_sentence: string; intended_word: string }
type Attempt = {
  answer: string
  score: number
  grade: Record<string, unknown>
}

export default function DrillsPage() {
  const [drill, setDrill] = useState<Drill | null>(null)
  const [answer, setAnswer] = useState('')
  const [attempt, setAttempt] = useState<Attempt | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function loadDrill() {
    setBusy(true)
    setError(null)
    setAttempt(null)
    setAnswer('')
    try {
      setDrill(await api.createDrill())
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed')
    } finally {
      setBusy(false)
    }
  }

  useEffect(() => {
    void loadDrill()
  }, [])

  async function onGrade(event: FormEvent) {
    event.preventDefault()
    if (!drill) return
    setBusy(true)
    setError(null)
    try {
      setAttempt(await api.gradeDrill(drill.id, answer))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Rewrite drill</h1>
          <p className="muted">Rewrite the vague sentence with a more precise word where it helps.</p>
        </div>
      </div>

      {error && <p className="error">{error}</p>}

      {!drill ? (
        <p className="muted">{busy ? 'Generating…' : 'No drill yet.'}</p>
      ) : (
        <>
          <p className="quote">{drill.vague_sentence}</p>
          {!attempt ? (
            <form className="panel stack" onSubmit={onGrade}>
              <label className="field">
                Your rewrite
                <textarea value={answer} onChange={(e) => setAnswer(e.target.value)} required />
              </label>
              <button type="submit" disabled={busy}>
                {busy ? 'Grading…' : 'Grade'}
              </button>
            </form>
          ) : (
            <section className="panel stack">
              <p>
                <strong>Your answer:</strong> {attempt.answer}
              </p>
              <p>
                <strong>Score:</strong> {attempt.score} / 5
              </p>
              <ul>
                <li>Precision: {String(attempt.grade.precision)}</li>
                <li>Meaning: {String(attempt.grade.meaning)}</li>
                <li>Naturalness: {String(attempt.grade.naturalness)}</li>
              </ul>
              <p>{String(attempt.grade.feedback || '')}</p>
              {attempt.grade.better_version ? (
                <p>
                  <strong>Better version:</strong> {String(attempt.grade.better_version)}
                </p>
              ) : null}
              <button type="button" onClick={() => void loadDrill()} disabled={busy}>
                Next
              </button>
            </section>
          )}
        </>
      )}
    </>
  )
}
