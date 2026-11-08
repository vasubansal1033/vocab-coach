import { useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'

type Option = {
  id: string
  word: string
  distinction: string
  example: string
  cloze: string
}

export default function ReviewPage() {
  const [option, setOption] = useState<Option | null | undefined>(undefined)
  const [answer, setAnswer] = useState('')
  const [error, setError] = useState<string | null>(null)

  function load() {
    api
      .review()
      .then((data) => {
        setOption(data.option)
        setAnswer('')
      })
      .catch((err: Error) => setError(err.message))
  }

  useEffect(() => {
    load()
  }, [])

  async function rate(event: FormEvent, rating: string) {
    event.preventDefault()
    if (!option) return
    try {
      await api.rateReview(option.id, rating, answer)
      load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed')
    }
  }

  if (option === undefined) return <p className="muted">Loading…</p>

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Review</h1>
          <p className="muted">Rate due cards when conversation practice is not enough.</p>
        </div>
      </div>
      {error && <p className="error">{error}</p>}
      {!option ? (
        <div className="panel">
          <p>No cards due. Keep chatting.</p>
          <Link to="/conversations">Conversations</Link>
        </div>
      ) : (
        <form className="panel stack">
          <p>
            <strong>Distinction:</strong> {option.distinction}
          </p>
          <p className="quote">{option.cloze}</p>
          <label className="field">
            Your word
            <input value={answer} onChange={(e) => setAnswer(e.target.value)} required />
          </label>
          <p className="muted">Rate how well you knew it:</p>
          <div className="rating-row">
            {['Again', 'Hard', 'Good', 'Easy'].map((rating) => (
              <button key={rating} className="rating" type="submit" onClick={(e) => rate(e, rating)}>
                {rating}
              </button>
            ))}
          </div>
        </form>
      )}
    </>
  )
}
