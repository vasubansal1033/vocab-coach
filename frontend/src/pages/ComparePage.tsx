import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api'

type CompareGroup = {
  id: string
  kind: string
  sense_gloss: string
  words: string[]
  has_strength_order: boolean
}

type CompareOption = {
  id: string
  word: string
  distinction: string
  example: string
  register: string
  collocations: string[]
  connotation: string | null
  strength: number | null
}

type CompareCard = {
  id: string
  kind: string
  sense_gloss: string
  pos: string
  options: CompareOption[]
  has_strength_order: boolean
}

type ExercisePromptOption = { option_id: string; word: string }

type Exercise = {
  id: string
  item_type: string
  prompt: {
    sentences?: string[]
    sentence?: string
    options?: ExercisePromptOption[]
  }
}

type Attempt = {
  id: string
  correct: boolean
  feedback: Record<string, unknown>
}

export default function ComparePage() {
  const { groupId } = useParams<{ groupId?: string }>()
  if (groupId) return <CompareCardView groupId={groupId} />
  return <CompareListView />
}

function CompareListView() {
  const [groups, setGroups] = useState<CompareGroup[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .listCompareGroups()
      .then(setGroups)
      .catch((err: Error) => setError(err.message))
  }, [])

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Compare</h1>
          <p className="muted">See how near-synonyms differ, then practise telling them apart.</p>
        </div>
      </div>
      {error && <p className="error">{error}</p>}
      {!groups ? (
        <p className="muted">Loading…</p>
      ) : groups.length === 0 ? (
        <p className="muted">No word sets yet.</p>
      ) : (
        <ul className="list">
          {groups.map((group) => (
            <li key={group.id}>
              <Link className="row" to={`/compare/${encodeURIComponent(group.id)}`}>
                <span>
                  <strong>{group.words.join(' · ')}</strong>
                  <span className="row-sub">{group.sense_gloss}</span>
                </span>
                <span className="muted">{group.kind}</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </>
  )
}

function CompareCardView({ groupId }: { groupId: string }) {
  const [card, setCard] = useState<CompareCard | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [exercise, setExercise] = useState<Exercise | null>(null)
  const [attempt, setAttempt] = useState<Attempt | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    api
      .getCompareCard(groupId)
      .then(setCard)
      .catch((err: Error) => setError(err.message))
  }, [groupId])

  async function startPractice(itemType: 'compare_pair' | 'compare_misuse' | 'compare_order') {
    setBusy(true)
    setError(null)
    setAttempt(null)
    try {
      const created = await api.createCompareExercise(groupId, itemType)
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
            <Link to="/compare">Compare</Link>
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
                <p>{opt.distinction}</p>
                <p className="quote">{opt.example}</p>
                <p className="muted">
                  Register: {opt.register}
                  {opt.connotation ? ` · Connotation: ${opt.connotation}` : ''}
                  {opt.strength != null ? ` · Strength: ${opt.strength}` : ''}
                </p>
                {opt.collocations.length > 0 ? (
                  <p className="muted">Collocations: {opt.collocations.join(', ')}</p>
                ) : null}
              </article>
            ))}
          </div>

          <section className="panel stack">
            <h2 className="panel-title">Practice</h2>
            <div className="rating-row">
              <button type="button" disabled={busy} onClick={() => void startPractice('compare_pair')}>
                Pair of sentences
              </button>
              <button
                type="button"
                disabled={busy}
                onClick={() => void startPractice('compare_misuse')}
              >
                Spot the misuse
              </button>
              {card.has_strength_order ? (
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => void startPractice('compare_order')}
                >
                  Order by strength
                </button>
              ) : null}
            </div>
          </section>

          {exercise ? (
            <PracticePanel
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

function PracticePanel({
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
  if (exercise.item_type === 'compare_pair') {
    return (
      <PairPractice
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
  if (exercise.item_type === 'compare_misuse') {
    return (
      <MisusePractice
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
    <OrderPractice
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

function PairPractice({
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
  const sentences = exercise.prompt.sentences ?? []
  const options = exercise.prompt.options ?? []
  const [picks, setPicks] = useState<string[]>(['', ''])

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    if (picks.some((p) => !p)) return
    onBusy(true)
    onError(null)
    try {
      const result = await api.answerExercise(exercise.id, { fits_option_ids: picks })
      onAttempt(result)
    } catch (err) {
      onError(err instanceof Error ? err.message : 'Failed')
    } finally {
      onBusy(false)
    }
  }

  const wordById = useMemo(
    () => new Map(options.map((o) => [o.option_id, o.word] as const)),
    [options],
  )

  return (
    <section className="panel stack">
      <h2 className="panel-title">Pair of sentences</h2>
      {!attempt ? (
        <form className="stack" onSubmit={onSubmit}>
          {sentences.map((sentence, index) => (
            <label key={index} className="field">
              {sentence}
              <select
                value={picks[index] ?? ''}
                onChange={(e) => {
                  const next = [...picks]
                  next[index] = e.target.value
                  setPicks(next)
                }}
                required
              >
                <option value="">Choose a word</option>
                {options.map((o) => (
                  <option key={o.option_id} value={o.option_id}>
                    {o.word}
                  </option>
                ))}
              </select>
            </label>
          ))}
          <button type="submit" disabled={busy}>
            {busy ? 'Checking…' : 'Check answer'}
          </button>
        </form>
      ) : (
        <FeedbackBlock
          correct={attempt.correct}
          lines={(attempt.feedback.fits_option_ids as string[] | undefined)?.map((id, i) => {
            const userId = (attempt.feedback.user_fits_option_ids as string[] | undefined)?.[i]
            return `Sentence ${i + 1}: ${wordById.get(id) ?? id}${
              userId && userId !== id ? ` (you chose ${wordById.get(userId) ?? userId})` : ''
            }`
          })}
          onClear={onClear}
        />
      )}
    </section>
  )
}

function MisusePractice({
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
  const options = exercise.prompt.options ?? []
  const [misused, setMisused] = useState('')
  const [replacement, setReplacement] = useState('')

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    if (!misused || !replacement) return
    onBusy(true)
    onError(null)
    try {
      const result = await api.answerExercise(exercise.id, {
        misused_option_id: misused,
        replacement_option_id: replacement,
      })
      onAttempt(result)
    } catch (err) {
      onError(err instanceof Error ? err.message : 'Failed')
    } finally {
      onBusy(false)
    }
  }

  const wordById = useMemo(
    () => new Map(options.map((o) => [o.option_id, o.word] as const)),
    [options],
  )

  return (
    <section className="panel stack">
      <h2 className="panel-title">Spot the misuse</h2>
      <p className="quote">{exercise.prompt.sentence}</p>
      {!attempt ? (
        <form className="stack" onSubmit={onSubmit}>
          <label className="field">
            Misused word
            <select value={misused} onChange={(e) => setMisused(e.target.value)} required>
              <option value="">Choose</option>
              {options.map((o) => (
                <option key={o.option_id} value={o.option_id}>
                  {o.word}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            Replace with
            <select value={replacement} onChange={(e) => setReplacement(e.target.value)} required>
              <option value="">Choose</option>
              {options.map((o) => (
                <option key={o.option_id} value={o.option_id}>
                  {o.word}
                </option>
              ))}
            </select>
          </label>
          <button type="submit" disabled={busy}>
            {busy ? 'Checking…' : 'Check answer'}
          </button>
        </form>
      ) : (
        <FeedbackBlock
          correct={attempt.correct}
          lines={[
            `Misused: ${wordById.get(String(attempt.feedback.misused_option_id)) ?? String(attempt.feedback.misused_option_id)}`,
            `Replace with: ${wordById.get(String(attempt.feedback.replacement_option_id)) ?? String(attempt.feedback.replacement_option_id)}`,
            String(attempt.feedback.reason ?? ''),
          ]}
          onClear={onClear}
        />
      )}
    </section>
  )
}

function OrderPractice({
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
  const options = exercise.prompt.options ?? []
  const [order, setOrder] = useState<string[]>(() => options.map((o) => o.option_id))

  useEffect(() => {
    setOrder(options.map((o) => o.option_id))
  }, [exercise.id])

  function move(index: number, delta: number) {
    const next = [...order]
    const target = index + delta
    if (target < 0 || target >= next.length) return
    ;[next[index], next[target]] = [next[target], next[index]]
    setOrder(next)
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    onBusy(true)
    onError(null)
    try {
      const result = await api.answerExercise(exercise.id, { ordered_option_ids: order })
      onAttempt(result)
    } catch (err) {
      onError(err instanceof Error ? err.message : 'Failed')
    } finally {
      onBusy(false)
    }
  }

  const wordById = useMemo(
    () => new Map(options.map((o) => [o.option_id, o.word] as const)),
    [options],
  )

  return (
    <section className="panel stack">
      <h2 className="panel-title">Order by strength</h2>
      <p className="muted">Weakest first, strongest last.</p>
      {!attempt ? (
        <form className="stack" onSubmit={onSubmit}>
          <ol className="plain-list">
            {order.map((id, index) => (
              <li key={id} className="choice-row">
                <span>{wordById.get(id) ?? id}</span>
                <button type="button" className="secondary" onClick={() => move(index, -1)}>
                  Up
                </button>
                <button type="button" className="secondary" onClick={() => move(index, 1)}>
                  Down
                </button>
              </li>
            ))}
          </ol>
          <button type="submit" disabled={busy}>
            {busy ? 'Checking…' : 'Check answer'}
          </button>
        </form>
      ) : (
        <FeedbackBlock
          correct={attempt.correct}
          lines={[
            `Correct: ${((attempt.feedback.ordered_option_ids as string[]) ?? [])
              .map((id) => wordById.get(id) ?? id)
              .join(' → ')}`,
            `Yours: ${((attempt.feedback.user_ordered_option_ids as string[]) ?? [])
              .map((id) => wordById.get(id) ?? id)
              .join(' → ')}`,
          ]}
          onClear={onClear}
        />
      )}
    </section>
  )
}

function FeedbackBlock({
  correct,
  lines,
  onClear,
}: {
  correct: boolean
  lines?: (string | undefined)[]
  onClear: () => void
}) {
  return (
    <div className="stack">
      <p>
        <strong>{correct ? 'Correct' : 'Not quite'}</strong>
      </p>
      <ul className="plain-list">
        {(lines ?? []).filter(Boolean).map((line) => (
          <li key={line}>{line}</li>
        ))}
      </ul>
      <button type="button" onClick={onClear}>
        Done
      </button>
    </div>
  )
}
