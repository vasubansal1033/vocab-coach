import { useEffect, useState, type FormEvent } from 'react'
import { api } from '../api'

const SET_SIZE = 5

type Drill = {
  id: string
  vague_sentence: string
  intended_word: string
  context: string | null
  intended_distinction: string | null
}

type Attempt = {
  id: string
  answer: string
  score: number
  grade: Record<string, unknown>
  hints_used: number
}

type Summary = {
  mean_score: number
  words_practised: string[]
  total_hints_used: number
}

export default function DrillsPage() {
  const [drill, setDrill] = useState<Drill | null>(null)
  const [answer, setAnswer] = useState('')
  const [attempt, setAttempt] = useState<Attempt | null>(null)
  const [hintsUsed, setHintsUsed] = useState(0)
  const [hintText, setHintText] = useState<string | null>(null)
  const [setIndex, setSetIndex] = useState(0)
  const [attemptIds, setAttemptIds] = useState<string[]>([])
  const [summary, setSummary] = useState<Summary | null>(null)
  const [disputed, setDisputed] = useState(false)
  const [disputeNote, setDisputeNote] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function loadDrill() {
    setBusy(true)
    setError(null)
    setAttempt(null)
    setAnswer('')
    setHintsUsed(0)
    setHintText(null)
    setDisputed(false)
    setDisputeNote('')
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
      const graded = await api.gradeDrill(drill.id, answer, hintsUsed)
      setAttempt(graded)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed')
    } finally {
      setBusy(false)
    }
  }

  async function onHint() {
    if (!drill || hintsUsed >= 3) return
    const nextLevel = (hintsUsed + 1) as 1 | 2 | 3
    setBusy(true)
    setError(null)
    try {
      const hint = await api.drillHint(drill.id, nextLevel)
      setHintsUsed(nextLevel)
      setHintText(hint.text)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed')
    } finally {
      setBusy(false)
    }
  }

  async function onNext() {
    if (!attempt) return
    const nextIds = [...attemptIds, attempt.id]
    const nextIndex = setIndex + 1
    if (nextIndex >= SET_SIZE) {
      setBusy(true)
      setError(null)
      try {
        setSummary(await api.drillSummary(nextIds))
        setAttemptIds([])
        setSetIndex(0)
        setDrill(null)
        setAttempt(null)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed')
      } finally {
        setBusy(false)
      }
      return
    }
    setAttemptIds(nextIds)
    setSetIndex(nextIndex)
    await loadDrill()
  }

  async function onDispute() {
    if (!attempt || disputed) return
    setBusy(true)
    setError(null)
    try {
      await api.disputeDrillAttempt(attempt.id, disputeNote.trim() || null)
      setDisputed(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed')
    } finally {
      setBusy(false)
    }
  }

  async function startNewSet() {
    setSummary(null)
    setAttemptIds([])
    setSetIndex(0)
    await loadDrill()
  }

  const betterVersion =
    attempt && typeof attempt.grade.better_version === 'string' && attempt.grade.better_version
      ? attempt.grade.better_version
      : null

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Rewrite drill</h1>
          <p className="muted">
            Rewrite the vague sentence with a more precise word where it helps. Sets of {SET_SIZE}.
          </p>
        </div>
        {!summary && (
          <p className="muted">
            Drill {Math.min(setIndex + 1, SET_SIZE)} of {SET_SIZE}
          </p>
        )}
      </div>

      {error && <p className="error">{error}</p>}

      {summary ? (
        <section className="panel stack">
          <h2>Set summary</h2>
          <p>
            Mean score: {summary.mean_score} / 5
          </p>
          <p>
            Words practised:{' '}
            {summary.words_practised.length ? summary.words_practised.join(', ') : 'none'}
          </p>
          <p>Hints used: {summary.total_hints_used}</p>
          <button type="button" onClick={() => void startNewSet()} disabled={busy}>
            Start another set
          </button>
        </section>
      ) : !drill ? (
        <p className="muted">{busy ? 'Generating…' : 'No drill yet.'}</p>
      ) : (
        <>
          {drill.context ? <p className="muted">{drill.context}</p> : null}
          <p className="quote">{drill.vague_sentence}</p>
          {!attempt ? (
            <form className="panel stack" onSubmit={onGrade}>
              <label className="field">
                Your rewrite
                <textarea value={answer} onChange={(e) => setAnswer(e.target.value)} required />
              </label>
              {hintText ? <p className="muted">Hint: {hintText}</p> : null}
              <div className="rating-row">
                <button type="button" className="secondary" onClick={() => void onHint()} disabled={busy || hintsUsed >= 3}>
                  {hintsUsed >= 3 ? 'All hints used' : `Hint (${hintsUsed}/3)`}
                </button>
                <button type="submit" disabled={busy}>
                  {busy ? 'Grading…' : 'Grade'}
                </button>
              </div>
            </form>
          ) : (
            <section className="panel stack">
              <p>
                <strong>Score:</strong> {attempt.score} / 5
                {attempt.hints_used > 0 ? ` · hints used: ${attempt.hints_used}` : null}
              </p>
              <ul>
                <li>Precision: {String(attempt.grade.precision)}</li>
                <li>Meaning: {String(attempt.grade.meaning)}</li>
                <li>Naturalness: {String(attempt.grade.naturalness)}</li>
              </ul>
              <div className="drill-compare">
                <div>
                  <h3>Your rewrite</h3>
                  <p>{attempt.answer}</p>
                </div>
                <div>
                  {betterVersion ? (
                    <>
                      <h3>Better version</h3>
                      <p>{betterVersion}</p>
                    </>
                  ) : (
                    <>
                      <h3>Intended</h3>
                      <p>
                        <strong>{drill.intended_word}</strong>
                        {drill.intended_distinction ? `: ${drill.intended_distinction}` : null}
                      </p>
                    </>
                  )}
                </div>
              </div>
              <p>{String(attempt.grade.feedback || '')}</p>
              {!disputed ? (
                <div className="stack">
                  <label className="field">
                    Dispute note (optional)
                    <input
                      value={disputeNote}
                      onChange={(e) => setDisputeNote(e.target.value)}
                      placeholder="Why does this grade look wrong?"
                    />
                  </label>
                  <button type="button" className="secondary" onClick={() => void onDispute()} disabled={busy}>
                    Dispute grade
                  </button>
                </div>
              ) : (
                <p className="muted">Dispute recorded.</p>
              )}
              <button type="button" onClick={() => void onNext()} disabled={busy}>
                {setIndex + 1 >= SET_SIZE ? 'Show summary' : 'Next'}
              </button>
            </section>
          )}
        </>
      )}
    </>
  )
}
