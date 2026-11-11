import { useEffect, useState, type FormEvent } from 'react'
import { api } from '../api'

const SET_SIZE = 5

type Tab = 'rewrite' | 'choice'

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

type ChoiceExercise = {
  id: string
  item_type: string
  prompt: {
    situation: string
    sentence: string
    candidates: { option_id: string; word: string }[]
  }
}

type ChoiceAttempt = {
  id: string
  correct: boolean
  feedback: {
    best_option_id?: string
    user_best_option_id?: string
    candidates?: {
      option_id: string
      fit: string
      reason: string
      best: boolean
      user_marked: boolean
    }[]
  }
}

export default function DrillsPage() {
  const [tab, setTab] = useState<Tab>('rewrite')

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Practice</h1>
          <p className="muted">Rewrite a vague sentence, or choose the word that fits a blank.</p>
        </div>
      </div>

      <div className="tabs" role="tablist" aria-label="Practice mode">
        <button
          type="button"
          role="tab"
          aria-selected={tab === 'rewrite'}
          className={tab === 'rewrite' ? 'tab active' : 'tab'}
          onClick={() => setTab('rewrite')}
        >
          Rewrite
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === 'choice'}
          className={tab === 'choice' ? 'tab active' : 'tab'}
          onClick={() => setTab('choice')}
        >
          Choose the word
        </button>
      </div>

      {tab === 'rewrite' ? <RewriteTab /> : <ChoiceTab />}
    </>
  )
}

function RewriteTab() {
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
          <h2>Rewrite drill</h2>
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
          <p>Mean score: {summary.mean_score} / 5</p>
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
                <button
                  type="button"
                  className="secondary"
                  onClick={() => void onHint()}
                  disabled={busy || hintsUsed >= 3}
                >
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
                  <button
                    type="button"
                    className="secondary"
                    onClick={() => void onDispute()}
                    disabled={busy}
                  >
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

function ChoiceTab() {
  const [exercise, setExercise] = useState<ChoiceExercise | null>(null)
  const [marked, setMarked] = useState<string[]>([])
  const [best, setBest] = useState<string>('')
  const [attempt, setAttempt] = useState<ChoiceAttempt | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function loadExercise() {
    setBusy(true)
    setError(null)
    setAttempt(null)
    setMarked([])
    setBest('')
    try {
      setExercise(await api.createChoiceExercise())
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed')
    } finally {
      setBusy(false)
    }
  }

  useEffect(() => {
    void loadExercise()
  }, [])

  function toggleMarked(optionId: string) {
    setMarked((prev) =>
      prev.includes(optionId) ? prev.filter((id) => id !== optionId) : [...prev, optionId],
    )
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    if (!exercise || !best) return
    setBusy(true)
    setError(null)
    try {
      const result = await api.answerExercise(exercise.id, {
        best_option_id: best,
        marked_option_ids: marked,
      })
      setAttempt(result as ChoiceAttempt)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed')
    } finally {
      setBusy(false)
    }
  }

  const wordById = new Map(
    (exercise?.prompt.candidates ?? []).map((c) => [c.option_id, c.word] as const),
  )

  return (
    <>
      <div className="page-head">
        <div>
          <h2>Choose the word</h2>
          <p className="muted">
            Mark every candidate that fits, then pick the best one for the blank.
          </p>
        </div>
      </div>

      {error && <p className="error">{error}</p>}

      {!exercise ? (
        <p className="muted">{busy ? 'Generating…' : 'No exercise yet.'}</p>
      ) : (
        <>
          <p className="muted">{exercise.prompt.situation}</p>
          <p className="quote">{exercise.prompt.sentence}</p>
          {!attempt ? (
            <form className="panel stack" onSubmit={onSubmit}>
              <fieldset className="stack">
                <legend>Which candidates fit?</legend>
                {exercise.prompt.candidates.map((c) => (
                  <label key={c.option_id} className="choice-row">
                    <input
                      type="checkbox"
                      checked={marked.includes(c.option_id)}
                      onChange={() => toggleMarked(c.option_id)}
                    />
                    <span>{c.word}</span>
                  </label>
                ))}
              </fieldset>
              <fieldset className="stack">
                <legend>Best fit</legend>
                {exercise.prompt.candidates.map((c) => (
                  <label key={c.option_id} className="choice-row">
                    <input
                      type="radio"
                      name="best"
                      value={c.option_id}
                      checked={best === c.option_id}
                      onChange={() => setBest(c.option_id)}
                      required
                    />
                    <span>{c.word}</span>
                  </label>
                ))}
              </fieldset>
              <button type="submit" disabled={busy || !best}>
                {busy ? 'Checking…' : 'Check answer'}
              </button>
            </form>
          ) : (
            <section className="panel stack">
              <p>
                <strong>{attempt.correct ? 'Correct' : 'Not quite'}</strong>
              </p>
              <ul className="choice-feedback">
                {(attempt.feedback.candidates ?? []).map((c) => (
                  <li key={c.option_id}>
                    <strong>{wordById.get(c.option_id) ?? c.option_id}</strong>
                    {c.best ? ' (best)' : ''} · {c.fit}
                    {c.user_marked ? ' · you marked fits' : ''}
                    <br />
                    <span className="muted">{c.reason}</span>
                  </li>
                ))}
              </ul>
              <button type="button" onClick={() => void loadExercise()} disabled={busy}>
                Next
              </button>
            </section>
          )}
        </>
      )}
    </>
  )
}
