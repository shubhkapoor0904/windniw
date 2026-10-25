type Props = {
  label: string
  value: string
  detail: string
  tone?: 'blue' | 'green' | 'amber' | 'purple'
}

export default function KpiCard({ label, value, detail, tone = 'blue' }: Props) {
  return (
    <article className={`kpi-card kpi-${tone}`} title={detail}>
      <div className="kpi-label">
        {label}
        <span className="info-mark" aria-label={detail}>i</span>
      </div>
      <div className="kpi-value">{value}</div>
      <p className="kpi-description">{detail}</p>
    </article>
  )
}
