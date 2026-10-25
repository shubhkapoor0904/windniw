import { useEffect, useMemo, useState } from 'react'
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { getLatest, type ForecastPoint, type LatestResponse } from '../api/client'
import AsyncState from '../components/AsyncState'
import Controls from '../components/Controls'
import KpiCard from '../components/KpiCard'
import WindTooltip from '../components/WindTooltip'
import { formatLocalTime, formatMetric, formatMw } from '../utils/formatters'

export default function DecisionView() {
  const [date, setDate] = useState('2026-01-15')
  const [cutoff, setCutoff] = useState('09:00')
  const [result, setResult] = useState<LatestResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let current = true
    setLoading(true)
    setError(null)
    getLatest(date, cutoff)
      .then((data) => { if (current) setResult(data) })
      .catch((reason: unknown) => {
        if (current) setError(reason instanceof Error ? reason.message : 'Unable to load forecast.')
      })
      .finally(() => { if (current) setLoading(false) })
    return () => { current = false }
  }, [date, cutoff])

  const chartData = useMemo(() => result?.data.map((point: ForecastPoint) => ({
    ...point,
    time: formatLocalTime(point.start_time),
    bandBase: point.uncertainty_low,
    bandWidth: point.uncertainty_low != null && point.uncertainty_high != null
      ? Math.max(0, point.uncertainty_high - point.uncertainty_low)
      : null,
  })) ?? [], [result])
  const summary = result?.summary

  return (
    <>
      <section className="section-header">
        <p className="eyebrow">Decision workspace / 01</p>
        <h1 className="section-title">Wind outlook</h1>
        <p className="section-description">
          See the latest wind forecast that would have been available when the day-ahead buying decision was made.
        </p>
      </section>
      <Controls
        start={date}
        end={date}
        cutoff={cutoff}
        onStart={setDate}
        onEnd={setDate}
        onCutoff={setCutoff}
        singleDate
      />
      <div className="assumption-note">
        <strong>Decision assumption</strong>
        <span>Cutoff is configurable and defaults to D-1 at {cutoff} Europe/London. Each point selects the most recently published forecast at or before that instant.</span>
      </div>
      <AsyncState loading={loading} error={error} empty={!loading && !error && chartData.length === 0} />
      {!loading && !error && chartData.length > 0 && (
        <>
          <div className="kpi-grid decision-kpis">
            <KpiCard label="Peak wind" value={formatMw(summary?.peak_mw)} detail="Highest forecast output in the selected delivery day." />
            <KpiCard label="Minimum wind" value={formatMw(summary?.min_mw)} detail="Lowest forecast output in the selected delivery day." tone="amber" />
            <KpiCard label="Average wind" value={formatMw(summary?.avg_mw)} detail="Average forecast power across available hourly delivery periods." tone="green" />
            <KpiCard label="Forecast energy" value={`${formatMetric(summary?.total_mwh)} MWh`} detail={`Forecast MW multiplied by the observed ${summary?.interval_hours ?? 1}-hour target interval.`} tone="purple" />
            <KpiCard label="Mean lead time" value={`${formatMetric(summary?.avg_horizon_hours, 1)} h`} detail="Average time between forecast publication and the delivery interval." tone="amber" />
          </div>
          <section className="card">
            <div className="card-header">
              <div>
                <h2 className="card-title">Hourly national wind forecast</h2>
                <p className="card-subtitle">{date} · WINDFOR is hourly in the observed feed · UTC stored, Europe/London displayed</p>
              </div>
              <span className="data-badge">{chartData.length} periods</span>
            </div>
            <div className="chart-container">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={chartData} margin={{ top: 10, right: 18, bottom: 0, left: 4 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="time" interval={5} minTickGap={24} />
                  <YAxis tickFormatter={(value: number) => `${Math.round(value / 1000)}k`} width={48} />
                  <Tooltip content={<WindTooltip />} />
                  <Area dataKey="bandBase" stackId="uncertainty" stroke="none" fill="transparent" name="Band base" tooltipType="none" isAnimationActive={false} />
                  <Area dataKey="bandWidth" stackId="uncertainty" stroke="none" fill="var(--chart-band)" name="Plausible range" connectNulls={false} isAnimationActive={false} />
                  <Line type="monotone" dataKey="generation_mw" name="Forecast" stroke="var(--chart-forecast)" strokeWidth={2.5} dot={false} activeDot={{ r: 4 }} connectNulls={false} isAnimationActive={false} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
            <div className="chart-legend">
              <span className="legend-item"><i className="legend-dot" style={{ background: 'var(--chart-forecast)' }} />Forecast</span>
              <span className="legend-item"><i className="legend-dot legend-band" />Historical P10–P90 plausible range</span>
            </div>
          </section>
          <section className="card point-table-card">
            <div className="card-header">
              <div><h2 className="card-title">Publication detail</h2><p className="card-subtitle">The source publication selected for each delivery period.</p></div>
            </div>
            <div className="table-scroll">
              <table>
                <thead><tr><th>Delivery time</th><th>Forecast</th><th>Plausible range</th><th>Published</th><th>Horizon</th></tr></thead>
                <tbody>{result?.data.map((point) => (
                  <tr key={point.start_time}>
                    <td>{formatLocalTime(point.start_time)}</td>
                    <td>{formatMw(point.generation_mw)}</td>
                    <td>{point.uncertainty_low == null || point.uncertainty_high == null ? '—' : `${Math.round(point.uncertainty_low).toLocaleString()}–${Math.round(point.uncertainty_high).toLocaleString()} MW`}</td>
                    <td>{new Intl.DateTimeFormat('en-GB', { timeZone: 'Europe/London', hour: '2-digit', minute: '2-digit' }).format(new Date(point.publish_time))}</td>
                    <td>{point.horizon_hours.toFixed(1)} h</td>
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
