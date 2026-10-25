import { useEffect, useMemo, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { getComparison, getMetrics, type ComparisonPoint, type MetricsResponse } from '../api/client'
import AsyncState from '../components/AsyncState'
import Controls from '../components/Controls'
import KpiCard from '../components/KpiCard'
import { downloadComparisonCsv } from '../utils/csv'
import { formatLocalDateTime, formatMetric } from '../utils/formatters'

export default function AccuracyView() {
  const [start, setStart] = useState('2026-01-01')
  const [end, setEnd] = useState('2026-01-31')
  const [cutoff, setCutoff] = useState('09:00')
  const [points, setPoints] = useState<ComparisonPoint[]>([])
  const [metrics, setMetrics] = useState<MetricsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let current = true
    setLoading(true)
    setError(null)
    Promise.all([getComparison(start, end, cutoff), getMetrics(start, end, cutoff)])
      .then(([comparison, metricResult]) => {
        if (current) {
          setPoints(comparison.data)
          setMetrics(metricResult)
        }
      })
      .catch((reason: unknown) => {
        if (current) setError(reason instanceof Error ? reason.message : 'Unable to load accuracy data.')
      })
      .finally(() => { if (current) setLoading(false) })
    return () => { current = false }
  }, [start, end, cutoff])

  const chartData = useMemo(() => points.map((point) => ({
    ...point,
    time: formatLocalDateTime(point.start_time),
  })), [points])
  const histogram = metrics?.error_distribution.map((bucket) => ({
    ...bucket,
    label: `${Math.round(bucket.bin_start)} to ${Math.round(bucket.bin_end)}`,
  })) ?? []
  const kpis = metrics?.metrics

  return (
    <>
      <section className="section-header">
        <p className="eyebrow">Performance / 02</p>
        <h1 className="section-title">Forecast accuracy</h1>
        <p className="section-description">Compare the decision-time hourly forecast with hourly mean outturn, calculated from two half-hour FUELHH observations. Incomplete actual hours and missing forecasts are excluded from error metrics.</p>
      </section>
      <Controls start={start} end={end} cutoff={cutoff} onStart={setStart} onEnd={setEnd} onCutoff={setCutoff} />
      <AsyncState loading={loading} error={error} empty={!loading && !error && points.length === 0} />
      {!loading && !error && points.length > 0 && (
        <>
          <div className="kpi-grid">
            <KpiCard label="MAE" value={`${formatMetric(kpis?.mae)} MW`} detail="Mean absolute error: the average size of the forecast miss, ignoring direction." />
            <KpiCard label="RMSE" value={`${formatMetric(kpis?.rmse)} MW`} detail="Root mean squared error: gives larger misses more weight than MAE." tone="purple" />
            <KpiCard label="Bias" value={`${formatMetric(kpis?.bias)} MW`} detail="Average forecast minus actual. Positive means wind was over-forecast." tone="amber" />
            <KpiCard label="MAPE" value={kpis?.mape == null ? '—' : `${formatMetric(kpis.mape, 1)}%`} detail="Average percentage miss; actuals below 1 MW are excluded to avoid division by zero." tone="green" />
            <KpiCard label="P90 miss" value={`${formatMetric(kpis?.p90_abs_error)} MW`} detail="Nine out of ten absolute forecast errors were at or below this level." />
          </div>
          <div className="section-actions">
            <span className="quiet-copy">{kpis?.count.toLocaleString()} matched hourly periods</span>
            <button className="btn btn-secondary" type="button" onClick={() => downloadComparisonCsv(points)}>Export comparison CSV</button>
          </div>
          <div className="grid-2 charts-grid">
            <section className="card">
              <div className="card-header"><div><h2 className="card-title">Error over time</h2><p className="card-subtitle">Forecast minus actual; points above zero indicate over-forecast wind.</p></div></div>
              <div className="chart-container">
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={chartData} margin={{ top: 10, right: 12, bottom: 0, left: 2 }}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="time" interval="preserveStartEnd" minTickGap={30} />
                    <YAxis />
                    <ReferenceLine y={0} stroke="rgba(164,190,215,.5)" strokeDasharray="4 4" />
                    <Tooltip formatter={(value: number) => [`${Math.round(value).toLocaleString()} MW`, 'Error']} />
                    <Line type="monotone" dataKey="error_mw" name="Error" stroke="var(--chart-error)" dot={false} connectNulls={false} isAnimationActive={false} />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </section>
            <section className="card">
              <div className="card-header"><div><h2 className="card-title">Forecast vs actual</h2><p className="card-subtitle">Hourly forecast and corresponding hourly mean actual, in MW.</p></div></div>
              <div className="chart-container">
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={chartData} margin={{ top: 10, right: 12, bottom: 0, left: 2 }}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="time" interval="preserveStartEnd" minTickGap={30} />
                    <YAxis tickFormatter={(value: number) => `${Math.round(value / 1000)}k`} width={48} />
                    <Tooltip labelFormatter={(label) => label} formatter={(value: number, name: string) => [`${Math.round(value).toLocaleString()} MW`, name]} />
                    <Line type="monotone" dataKey="forecast_mw" name="Forecast" stroke="var(--chart-forecast)" dot={false} connectNulls={false} isAnimationActive={false} />
                    <Line type="monotone" dataKey="actual_mw" name="Actual" stroke="var(--chart-actual)" dot={false} connectNulls={false} isAnimationActive={false} />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </section>
            <section className="card">
              <div className="card-header"><div><h2 className="card-title">Error distribution</h2><p className="card-subtitle">Forecast minus actual · positive values are over-forecasts.</p></div></div>
              <div className="chart-container">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={histogram} margin={{ top: 10, right: 12, bottom: 22, left: 2 }}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="label" angle={-35} textAnchor="end" interval={Math.max(0, Math.floor(histogram.length / 8) - 1)} />
                    <YAxis />
                    <Tooltip formatter={(value: number) => [value, 'Periods']} labelFormatter={(label) => `${label} MW error`} />
                    <Bar dataKey="count" name="Periods" fill="var(--chart-actual)" radius={[3, 3, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </section>
          </div>
          <section className="card point-table-card">
            <div className="card-header"><div><h2 className="card-title">Comparison records</h2><p className="card-subtitle">Export includes all returned periods, including rows with missing values.</p></div></div>
            <div className="table-scroll">
              <table>
                <thead><tr><th>Delivery time</th><th>Forecast MW</th><th>Actual MW</th><th>Error MW</th><th>Publication</th><th>Horizon</th></tr></thead>
                <tbody>{points.map((point) => (
                  <tr key={point.start_time}>
                    <td>{formatLocalDateTime(point.start_time)}</td>
                    <td>{formatMetric(point.forecast_mw)}</td>
                    <td>{formatMetric(point.actual_mw)}</td>
                    <td className={point.error_mw != null && point.error_mw > 0 ? 'positive-error' : ''}>{formatMetric(point.error_mw)}</td>
                    <td>{point.publish_time ? formatLocalDateTime(point.publish_time) : '—'}</td>
                    <td>{point.horizon_hours == null ? '—' : `${point.horizon_hours.toFixed(1)} h`}</td>
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
