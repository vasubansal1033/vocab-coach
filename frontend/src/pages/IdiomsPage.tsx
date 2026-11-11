import { useEffect, useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api'

type IdiomGroup = {
  id: string
  head_lemma: string | null
  sense_gloss: string
  words: string[]
  tier: string
}

type IdiomOption = {
  id: string
  word: string
  distinction: string
  example: string
  register: string
  meaning: string
  tier: string
  region: string
  variants: string[]
  misuse_example: string
  avoid_when: string
  origin: string | null
}

type IdiomCard = {
  id: string
  head_lemma: string | null
  sense_gloss: string
  pos: string
  options: IdiomOption[]
}

type Exercise = {
  id: string
  item_type: string
  prompt: {
    stem?: string
    word?: string | null
    choices?: { id: string; label: string }[]
    option_id?: string
    meaning?: string
    avoid_when?: string
  }
}

type Attempt = {
  id: string
  correct: boolean
  feedback: Record<string, unknown>
}

type IdiomStep = 'idiom_recognise' | 'idiom_meaning' | 'idiom_situation' | 'idiom_write'

export default function IdiomsPage() {
  const { groupId } = useParams<{ groupId?: string }>()
  if (groupId) return <IdiomCardView groupId={groupId} />
  return <IdiomListView />
}

function IdiomListView() {
  const [groups, setGroups] = useState<IdiomGroup[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .listIdiomGroups()
      .then(setGroups)
      .catch((err: Error) => setError(err.message))
  }, [])

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Idioms</h1>
          <p className="muted">
            Learn workplace idioms in steps. Each card shows when to avoid the phrase.
          </p>
        </div>
      </div>
      {error && <p className="error">{error}</p>}
      {!groups ? (
        <p className="muted">Loading…</p>
      ) : groups.length === 0 ? (
        <p className="muted">No idioms loaded yet.</p>
      ) : (
        <ul className="list">
          {groups.map((group) => (
            <li key={group.id}>
              <Link className="row" to={`/idioms/${encodeURIComponent(group.id)}`}>
                <span>
                  <strong>{group.words.join(' · ')}</strong>
                  <span className="row-sub">{group.sense_gloss}</span>
                </span>
                <span className="muted">{group.tier}</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </>
  )
}

function IdiomCardView({ groupId }: { groupId: string }) {
  const [card, setCard] = useState<IdiomCard | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [exercise, setExercise] = useState<Exercise | null>(null)
  const [attempt, setAttempt] = useState<Attempt | null>(null)
  const [busy, setBusy] = useState(false)
  const [activeOptionId, setActiveOptionId] = useState<string | null>(null)

  useEffect(() => {
    api
      .getIdiomCard(groupId)
      .then((next) => {
        setCard(next)
        setActiveOptionId(next.options[0]?.id ?? null)
      })
      .catch((err: Error) => setError(err.message))
  }, [groupId])

  async function startStep(itemType: IdiomStep) {
    if (!activeOptionId && itemType === 'idiom_write') return
    setBusy(true)
    setError(null)
    setAttempt(null)
    try {
      const created = await api.createIdiomExercise(groupId, itemType, activeOptionId ?? undefined)
      setExercise({
        id: created.id,
        item_type: created.item_type,
        prompt: created.prompt as Exercise['prompt'],
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed')
    } finally {
      setBusy(false)
    }
  }

  if (!card && !error) return <p className="muted">Loading…</p>

  return (
    <>
      <div className="page-head">
        <div>
          <p className="muted">
            <Link to="/idioms">Idioms</Link>
          </p>
          <h1>{card ? card.options.map((o) => o.word).join(' · ') : groupId}</h1>
          {card ? <p className="muted">{card.sense_gloss}</p> : null}
        </div>
      </div>
      {error && <p className="error">{error}</p>}
      {card ? (
        <>
          <div className="compare-grid">
            {card.options.map((opt) => (
              <article key={opt.id} className="panel stack">
                <h2 className="panel-title">{opt.word}</h2>
                <p>{opt.meaning}</p>
                <p className="quote">{opt.example}</p>
                <p>
                  <strong>Avoid when:</strong> {opt.avoid_when || '—'}
                </p>
                <p className="muted">Misuse: {opt.misuse_example || '—'}</p>
                {opt.origin ? <p className="muted">Origin: {opt.origin}</p> : null}
                <p className="muted">
                  {opt.tier} · {opt.region}
                  {opt.variants.length ? ` · also: ${opt.variants.join(', ')}` : ''}
                </p>
                <button
                  type="button"
                  className={activeOptionId === opt.id ? 'primary' : undefined}
                  onClick={() => setActiveOptionId(opt.id)}
                >
                  Practise this idiom
                </button>
              </article>
            ))}
          </div>

          <section className="panel stack">
            <h2 className="panel-title">Steps</h2>
            <p className="muted">
              Recognise, meaning, situation, then write your own sentence. Unprompted use in
              conversation is step 5 and needs no button here.
            </p>
            <div className="rating-row">
              <button type="button" disabled={busy} onClick={() => void startStep('idiom_recognise')}>
                1. Recognise
              </button>
              <button type="button" disabled={busy} onClick={() => void startStep('idiom_meaning')}>
                2. Meaning
              </button>
              <button
                type="button"
                disabled={busy}
                onClick={() => void startStep('idiom_situation')}
              >
                3. Situation
              </button>
              <button
                type="button"
                disabled={busy || !activeOptionId}
                onClick={() => void startStep('idiom_write')}
              >
                4. Write a sentence
              </button>
            </div>
          </section>

          {exercise ? (
            <IdiomPractice
              exercise={exercise}
              attempt={attempt}
              busy={busy}
              onBusy={setBusy}
              onError={setError}
              onAttempt={setAttempt}
              onClear={() => {
                setExercise(null)
                setAttempt(null)
              }}
            />
          ) : null}
        </>
      ) : null}
    </>
  )
}

function IdiomPractice({
  exercise,
  attempt,
  busy,
  onBusy,
  onError,
  onAttempt,
  onClear,
}: {
  exercise: Exercise
  attempt: Attempt | null
  busy: boolean
  onBusy: (v: boolean) => void
  onError: (v: string | null) => void
  onAttempt: (v: Attempt) => void
  onClear: () => void
}) {
  if (exercise.item_type === 'idiom_write') {
    return (
      <WritePractice
        exercise={exercise}
        attempt={attempt}
        busy={busy}
        onBusy={onBusy}
        onError={onError}
        onAttempt={onAttempt}
        onClear={onClear}
      />
    )
  }
  return (
    <SelectPractice
      exercise={exercise}
      attempt={attempt}
      busy={busy}
      onBusy={onBusy}
      onError={onError}
      onAttempt={onAttempt}
      onClear={onClear}
    />
  )
}

function SelectPractice({
  exercise,
  attempt,
  busy,
  onBusy,
  onError,
  onAttempt,
  onClear,
}: {
  exercise: Exercise
  attempt: Attempt | null
  busy: boolean
  onBusy: (v: boolean) => void
  onError: (v: string | null) => void
  onAttempt: (v: Attempt) => void
  onClear: () => void
}) {
  const choices = exercise.prompt.choices ?? []
  const [selectedId, setSelectedId] = useState('')

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    if (!selectedId) return
    onBusy(true)
    onError(null)
    try {
      const result = await api.answerExercise(exercise.id, { selected_id: selectedId })
      onAttempt(result)
    } catch (err) {
      onError(err instanceof Error ? err.message : 'Failed')
    } finally {
      onBusy(false)
    }
  }

  const title =
    exercise.item_type === 'idiom_recognise'
      ? 'Recognise the idiom'
      : exercise.item_type === 'idiom_meaning'
        ? 'Choose the meaning'
        : 'Choose the situation'

  return (
    <section className="panel stack">
      <h2 className="panel-title">{title}</h2>
      {exercise.prompt.word ? <p className="quote">{exercise.prompt.word}</p> : null}
      <p>{exercise.prompt.stem}</p>
      {!attempt ? (
        <form className="stack" onSubmit={onSubmit}>
          {choices.map((choice) => (
            <label key={choice.id} className="field">
              <input
                type="radio"
                name="idiom-choice"
                value={choice.id}
                checked={selectedId === choice.id}
                onChange={() => setSelectedId(choice.id)}
                required
              />{' '}
              {choice.label}
            </label>
          ))}
          <button type="submit" disabled={busy || !selectedId}>
            {busy ? 'Checking…' : 'Check answer'}
          </button>
        </form>
      ) : (
        <div className="stack">
          <p className={attempt.correct ? 'ok' : 'error'}>
            {attempt.correct ? 'Correct.' : 'Not quite.'}
          </p>
          <button type="button" onClick={onClear}>
            Done
          </button>
        </div>
      )}
    </section>
  )
}

function WritePractice({
  exercise,
  attempt,
  busy,
  onBusy,
  onError,
  onAttempt,
  onClear,
}: {
  exercise: Exercise
  attempt: Attempt | null
  busy: boolean
  onBusy: (v: boolean) => void
  onError: (v: string | null) => void
  onAttempt: (v: Attempt) => void
  onClear: () => void
}) {
  const [sentence, setSentence] = useState('')

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    if (!sentence.trim()) return
    onBusy(true)
    onError(null)
    try {
      const result = await api.answerExercise(exercise.id, { sentence: sentence.trim() })
      onAttempt(result)
    } catch (err) {
      onError(err instanceof Error ? err.message : 'Failed')
    } finally {
      onBusy(false)
    }
  }

  return (
    <section className="panel stack">
      <h2 className="panel-title">Write a sentence</h2>
      <p className="quote">{exercise.prompt.word}</p>
      <p>{exercise.prompt.meaning}</p>
      {exercise.prompt.avoid_when ? (
        <p className="muted">Avoid when: {exercise.prompt.avoid_when}</p>
      ) : null}
      {!attempt ? (
        <form className="stack" onSubmit={onSubmit}>
          <label className="field">
            Your sentence
            <textarea
              value={sentence}
              onChange={(e) => setSentence(e.target.value)}
              rows={3}
              required
            />
          </label>
          <button type="submit" disabled={busy || !sentence.trim()}>
            {busy ? 'Checking…' : 'Check sentence'}
          </button>
        </form>
      ) : (
        <div className="stack">
          <p className={attempt.correct ? 'ok' : 'error'}>
            {attempt.correct ? 'Correct use.' : 'Not quite.'}
          </p>
          {typeof attempt.feedback.explanation === 'string' ? (
            <p>{attempt.feedback.explanation}</p>
          ) : null}
          <button type="button" onClick={onClear}>
            Done
          </button>
        </div>
      )}
    </section>
  )
}
