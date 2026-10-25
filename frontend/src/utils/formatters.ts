export function formatMw(value: number | null | undefined): string {
  return value == null ? '—' : `${Math.round(value).toLocaleString('en-GB')} MW`
}

export function formatMetric(value: number | null | undefined, digits = 0): string {
  return value == null
    ? '—'
    : value.toLocaleString('en-GB', { maximumFractionDigits: digits })
}

export function formatLocalTime(isoDate: string): string {
  return new Intl.DateTimeFormat('en-GB', {
    timeZone: 'Europe/London',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(isoDate))
}

export function formatLocalDateTime(isoDate: string): string {
  return new Intl.DateTimeFormat('en-GB', {
    timeZone: 'Europe/London',
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(isoDate))
}
