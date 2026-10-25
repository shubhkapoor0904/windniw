type Props = {
  loading: boolean
  error: string | null
  empty?: boolean
}

export default function AsyncState({ loading, error, empty = false }: Props) {
  if (loading) {
    return <div className="loading-state"><span className="loading-spinner" />Loading cached market data…</div>
  }
  if (error) {
    return <div className="error-banner" role="alert">{error}</div>
  }
  if (empty) {
    return <div className="empty-state">No matching cached observations for this selection.</div>
  }
  return null
}
