import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import {
  CategoryScale,
  Chart as ChartJS,
  LinearScale,
  LineElement,
  PointElement,
  Tooltip,
} from 'chart.js'
import { Line } from 'react-chartjs-2'
import { api, type Dashboard } from '../api'
import InfoTip from '../components/InfoTip'
import { METRIC_DEFINITIONS } from '../metricsCopy'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip)

function pct(value: number | null) {
  return value == null ? '—' : `${Math.round(value * 100)}%`
}

function shortWeekLabel(isoDate: string): string {
  const parsed = new Date(`${isoDate}T00:00:00Z`)
  if (Number.isNaN(parsed.getTime())) return isoDate
  return parsed.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    timeZone: 'UTC',
  })
}

export default function DashboardPage() {
  const [data, setData] = useState<Dashboard | null>(null)
  const [promptVersion, setPromptVersion] = useState('')
  const [model, setModel] = useState('')
  const [error, setError] = useState<string | null>(null)

  function load(next?: { prompt_version?: string; model?: string }) {
    api
      .dashboard(next)
      .then(setData)
      .catch((err: Error) => setError(err.message))
  }

  useEffect(() => {
    load()
  }, [])

  const chart = useMemo(() => {
    if (!data) return null
    return {
      labels: data.weekly.map((w) => shortWeekLabel(w.label)),
      datasets: [
        {
          label: 'Crutch rate / 1000 words',
          data: data.weekly.map((w) => w.rate ?? null),
          borderColor: '#0f766e',
          backgroundColor: 'rgba(15, 118, 110, 0.2)',
          tension: 0.25,
          spanGaps: false,
        },
      ],
    }
  }, [data])

  const drillChart = useMemo(() => {
    if (!data) return null
    const weeks = data.drill_weeks.filter((w) => w.score != null)
    if (!weeks.length) return null
    return {
      labels: weeks.map((w) => shortWeekLabel(w.label)),
      datasets: [
        {
          label: 'Mean drill score (1–5)',
          data: weeks.map((w) => w.score),
          borderColor: '#c2410c',
          backgroundColor: 'rgba(194, 65, 12, 0.2)',
          tension: 0.25,
        },
      ],
    }
  }, [data])

  function onFilter(event: FormEvent) {
    event.preventDefault()
    load({
      prompt_version: promptVersion || undefined,
      model: model || undefined,
    })
  }

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Dashboard</h1>
          <p className="muted">
            {data ? `Last twelve weeks ending ${data.window_end.slice(0, 10)}.` : 'Loading metrics…'}
          </p>
        </div>
      </div>

      {error && <p className="error">{error}</p>}

      {data && (
        <>
          <div className="metrics">
            <div className="metric">
              <InfoTip label="Crutch rate" definition={METRIC_DEFINITIONS.crutchRate} />
              <strong>{data.crutch_rate == null ? '—' : data.crutch_rate.toFixed(1)}</strong>
            </div>
            <div className="metric">
              <InfoTip label="Acceptance" definition={METRIC_DEFINITIONS.acceptance} />
              <strong>{pct(data.acceptance)}</strong>
            </div>
            <div className="metric">
              <InfoTip label="Spontaneous" definition={METRIC_DEFINITIONS.spontaneous} />
              <strong>{pct(data.spontaneous)}</strong>
            </div>
            <div className="metric">
              <InfoTip label="Misuse" definition={METRIC_DEFINITIONS.misuse} />
              <strong>{pct(data.misuse)}</strong>
            </div>
            <div className="metric">
              <InfoTip label="Idiom misuse" definition={METRIC_DEFINITIONS.idiomMisuse} />
              <strong>{pct(data.idiom_misuse)}</strong>
            </div>
            <div className="metric">
              <InfoTip label="MTLD" definition={METRIC_DEFINITIONS.mtld} />
              <strong>{data.mtld == null ? '—' : data.mtld.toFixed(1)}</strong>
            </div>
          </div>

          <section className="panel">
            <h2>
              <InfoTip label="Weekly crutch rate" definition={METRIC_DEFINITIONS.crutchRate} />
            </h2>
            {chart && (
              <div className="chart-frame">
                <Line
                  data={chart}
                  options={{
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                      y: { beginAtZero: true },
                      x: { ticks: { maxRotation: 0, autoSkip: true, maxTicksLimit: 6 } },
                    },
                    plugins: {
                      tooltip: {
                        callbacks: {
                          label: (ctx) =>
                            ctx.parsed.y == null
                              ? 'No data'
                              : `${ctx.parsed.y.toFixed(1)} per 1000 words`,
                        },
                      },
                    },
                  }}
                />
              </div>
            )}
          </section>

          <section className="panel">
            <h2>
              <InfoTip label="Overused words" definition={METRIC_DEFINITIONS.overuseLift} />
            </h2>
            {!data.overuse.length ? (
              <p className="muted">No surface forms with five or more uses yet.</p>
            ) : (
              <table className="table">
                <thead>
                  <tr>
                    <th>Word</th>
                    <th>Uses</th>
                    <th>
                      <InfoTip label="Lift" definition={METRIC_DEFINITIONS.overuseLift} />
                    </th>
                    <th>Groups</th>
                  </tr>
                </thead>
                <tbody>
                  {data.overuse.map((row) => (
                    <tr key={row.word}>
                      <td>
                        <Link to={`/dashboard/lemma/${encodeURIComponent(row.word)}`}>{row.word}</Link>
                      </td>
                      <td>{row.uses}</td>
                      <td>{Math.round(row.lift)}×</td>
                      <td>{row.groups.map((g) => g.id).join(', ')}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>

          <section className="panel">
            <h2>
              <InfoTip label="Acceptance filter" definition={METRIC_DEFINITIONS.acceptance} />
            </h2>
            <form className="stack" onSubmit={onFilter}>
              <label className="field">
                prompt_version
                <input value={promptVersion} onChange={(e) => setPromptVersion(e.target.value)} />
              </label>
              <label className="field">
                model
                <input value={model} onChange={(e) => setModel(e.target.value)} />
              </label>
              <button type="submit">Filter</button>
            </form>
          </section>

          <section className="panel">
            <h2>
              <InfoTip label="Drill score" definition={METRIC_DEFINITIONS.drillScore} />
            </h2>
            {!drillChart ? (
              <p className="muted">No graded drills in this window yet.</p>
            ) : (
              <div className="chart-frame">
                <Line
                  data={drillChart}
                  options={{
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                      y: { min: 1, max: 5, ticks: { stepSize: 1 } },
                      x: { ticks: { maxRotation: 0, autoSkip: true, maxTicksLimit: 6 } },
                    },
                    plugins: {
                      tooltip: {
                        callbacks: {
                          label: (ctx) =>
                            ctx.parsed.y == null ? '—' : `Score ${ctx.parsed.y.toFixed(1)} / 5`,
                        },
                      },
                    },
                  }}
                />
              </div>
            )}
          </section>
        </>
      )}
    </>
  )
}
