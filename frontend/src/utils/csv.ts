import type { ComparisonPoint } from '../api/client'

function escapeCsv(value: string | number | null): string {
  const text = value == null ? '' : String(value)
  return `"${text.replace(/"/g, '""')}"`
}

export function comparisonToCsv(points: ComparisonPoint[]): string {
  const headers = [
    'start_time_utc',
    'actual_mw',
    'forecast_mw',
    'publish_time_utc',
    'horizon_hours',
    'error_mw',
    'absolute_error_mw',
  ]
  const rows = points.map((point) => [
    point.start_time,
    point.actual_mw,
    point.forecast_mw,
    point.publish_time,
    point.horizon_hours,
    point.error_mw,
    point.abs_error_mw,
  ])
  return [headers, ...rows].map((row) => row.map(escapeCsv).join(',')).join('\r\n')
}

export function downloadComparisonCsv(points: ComparisonPoint[]): void {
  const blob = new Blob([comparisonToCsv(points)], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = 'wind-forecast-comparison.csv'
  link.click()
  URL.revokeObjectURL(url)
}
