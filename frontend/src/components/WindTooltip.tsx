type Payload = {
  name?: string
  value?: number | null
  color?: string
  dataKey?: string
  payload?: Record<string, unknown>
}
type Props = {
  active?: boolean
  label?: string
  payload?: Payload[]
}

export default function WindTooltip({ active, label, payload }: Props) {
  if (!active || !payload?.length) return null
  const point = payload[0]?.payload
  return (
    <div className="chart-tooltip">
      <div className="chart-tooltip-label">{label}</div>
      {payload.filter((item) => item.value != null).map((item) => (
        <div className="tooltip-row" key={item.dataKey}>
          <span style={{ color: item.color }}>{item.name}</span>
          <strong>{Math.round(Number(item.value)).toLocaleString('en-GB')} MW</strong>
        </div>
      ))}
      {typeof point?.publish_time === 'string' && (
        <div className="tooltip-meta">Published {new Date(point.publish_time).toLocaleString('en-GB', { timeZone: 'Europe/London' })}</div>
      )}
      {typeof point?.horizon_hours === 'number' && (
        <div className="tooltip-meta">{point.horizon_hours.toFixed(1)} h forecast horizon</div>
      )}
    </div>
  )
}
