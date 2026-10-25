import { useEffect, useState } from 'react'
import {
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { getHorizon, type HorizonBucket } from '../api/client'
import AsyncState from '../components/AsyncState'
import Controls from '../components/Controls'

export default function HorizonView() {
  const [start, setStart] = useState('2026-01-01')
  const [end, setEnd] = useState('2026-01-31')
  const [cutoff, setCutoff] = useState('09:00')
  const [buckets, setBuckets] = useState<HorizonBucket[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let current = true
    setLoading(true)
    setError(null)
    getHorizon(start, end, cutoff)
      .then((data) => { if (current) setBuckets(data.buckets) })
      .catch((reason: unknown) => {
        if (current) setError(reason instanceof Error ? reason.message : 'Unable to load horizon analysis.')
      })
      .finally(() => { if (current) setLoading(false) })
    return () => { current = false }
  }, [start, end, cutoff])

  return (
    <>
      <section className="section-header">
        <p className="eyebrow">Trust by lead time / 03</p>
        <h1 className="section-title">How forecast age changes error</h1>
        <p className="section-description">The lead time is the gap between publication and delivery. Larger errors at longer horizons mean buyers should plan for wider uncertainty when relying on older forecasts.</p>
      </section>
      <Controls start={start} end={end} cutoff={cutoff} onStart={setStart} onEnd={setEnd} onCutoff={setCutoff} />
      <AsyncState loading={loading} error={error} empty={!loading && !error && buckets.length === 0} />
      {!loading && !error && buckets.length > 0 && (
        <>
          <section className="card">
            <div className="card-header"><div><h2 className="card-title">Error by forecast horizon</h2><p className="card-subtitle">MAE and signed bias, MW. Bias above zero means the forecast was higher than actual wind.</p></div></div>
            <div className="chart-container">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={buckets} margin={{ top: 12, right: 16, bottom: 0, left: 2 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="horizon_label" />
                  <YAxis />
                  <Tooltip formatter={(value: number, name: string) => [`${value.toLocaleString()} MW`, name]} />
                  <Line type="monotone" dataKey="mae" name="MAE" stroke="var(--chart-forecast)" strokeWidth={3} isAnimationActive={false} />
                  <Line type="monotone" dataKey="bias" name="Bias" stroke="var(--accent-warning)" strokeWidth={2} isAnimationActive={false} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </section>
          <section className="card point-table-card">
            <div className="card-header"><div><h2 className="card-title">Horizon reference</h2><p className="card-subtitle">Signed P10/P90 error quantiles are used to frame the plausible generation range.</p></div></div>
            <div className="table-scroll">
              <table>
                <thead><tr><th>Horizon</th><th>Periods</th><th>MAE MW</th><th>RMSE MW</th><th>Bias MW</th><th>P10 error</th><th>P90 error</th></tr></thead>
                <tbody>{buckets.map((bucket) => (
                  <tr key={bucket.horizon_label}>
                    <td>{bucket.horizon_label}</td><td>{bucket.count.toLocaleString()}</td>
                    <td>{Math.round(bucket.mae).toLocaleString()}</td><td>{Math.round(bucket.rmse).toLocaleString()}</td>
                    <td>{Math.round(bucket.bias).toLocaleString()}</td><td>{Math.round(bucket.p10_error).toLocaleString()}</td>
                    <td>{Math.round(bucket.p90_error).toLocaleString()}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          </section>
        </>
      )}
    </>
  )
}
