import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api'

export default function LemmaPage() {
  const { lemma = '' } = useParams()
  const [data, setData] = useState<{
    lemma: string
    weekly: { label: string; rate: number | null }[]
    options: { option_id: string; word: string; uses: number; correct_uses: number }[]
  } | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .lemma(lemma)
      .then(setData)
      .catch((err: Error) => setError(err.message))
  }, [lemma])

  return (
    <>
      <p>
        <Link to="/dashboard">← Dashboard</Link>
      </p>
      <div className="page-head">
        <div>
          <h1>{lemma}</h1>
          <p className="muted">Weekly crutch rate and learned options for this lemma.</p>
        </div>
      </div>
      {error && <p className="error">{error}</p>}
      {data && (
        <>
          <section className="panel">
            <h2>Weekly rate</h2>
            {!data.weekly.some((w) => w.rate != null) ? (
              <p className="muted">No uses of this lemma in the window yet.</p>
            ) : (
              <table className="table">
                <thead>
                  <tr>
                    <th>Week ending</th>
                    <th>Rate / 1000</th>
                  </tr>
                </thead>
                <tbody>
                  {data.weekly
                    .filter((w) => w.rate != null)
                    .map((w) => (
                      <tr key={w.label}>
                        <td>{w.label}</td>
                        <td>{w.rate!.toFixed(1)}</td>
                      </tr>
                    ))}
                </tbody>
              </table>
            )}
          </section>
          <section className="panel">
            <h2>Learned options</h2>
            {!data.options.length ? (
              <p className="muted">No accepted options from this lemma's groups in the window.</p>
            ) : (
              <table className="table">
                <thead>
                  <tr>
                    <th>Word</th>
                    <th>Uses</th>
                    <th>Correct</th>
                  </tr>
                </thead>
                <tbody>
                  {data.options.map((opt) => (
                    <tr key={opt.option_id}>
                      <td>{opt.word}</td>
                      <td>{opt.uses}</td>
                      <td>{opt.correct_uses}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>
        </>
      )}
    </>
  )
}
