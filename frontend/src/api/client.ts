export type ForecastPoint = {
  start_time: string
  publish_time: string
  generation_mw: number
  horizon_hours: number
  uncertainty_low: number | null
  uncertainty_high: number | null
}

export type LatestResponse = {
  target_date: string
  cutoff_time: string
  data: ForecastPoint[]
  summary: {
    peak_mw: number
    min_mw: number
    avg_mw: number
    total_mwh: number
    avg_horizon_hours: number
    interval_hours: number
  } | null
}

export type ComparisonPoint = {
  start_time: string
  actual_mw: number | null
  forecast_mw: number | null
  publish_time: string | null
  horizon_hours: number | null
  error_mw: number | null
  abs_error_mw: number | null
}

export type Metrics = {
  mae: number | null
  rmse: number | null
  mape: number | null
  bias: number | null
  p50_abs_error: number | null
  p90_abs_error: number | null
  p99_abs_error: number | null
  nmae: number | null
  count: number
}

export type MetricsResponse = {
  start_date: string
  end_date: string
  cutoff_hour: number
  cutoff_minute: number
  metrics: Metrics
  error_distribution: { bin_start: number; bin_end: number; count: number }[]
}

export type HorizonBucket = {
  horizon_label: string
  horizon_min_hours: number
  horizon_max_hours: number
  mae: number
  rmse: number
  bias: number
  p10_error: number
  p90_error: number
  count: number
}

const baseUrl = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')

async function get<T>(path: string, params: Record<string, string>): Promise<T> {
  const query = new URLSearchParams(params)
  const response = await fetch(`${baseUrl}/api/${path}?${query.toString()}`)
  if (!response.ok) {
    let message = `Request failed (${response.status})`
    try {
      const body = await response.json()
      message = body.detail ?? message
    } catch {
      // Keep the HTTP status message if the server did not return JSON.
    }
    throw new Error(message)
  }
  return response.json() as Promise<T>
}

export function cutoffParams(cutoff: string): Record<string, string> {
  const [hour, minute] = cutoff.split(':')
  return { cutoffHour: String(Number(hour)), cutoffMinute: String(Number(minute)) }
}

export function getLatest(targetDate: string, cutoff: string): Promise<LatestResponse> {
  return get('forecast/latest', {
    targetDate,
    ...cutoffParams(cutoff),
  })
}

export function getComparison(
  start: string,
  end: string,
  cutoff: string,
): Promise<{ data: ComparisonPoint[]; count: number }> {
  return get('compare', { start, end, ...cutoffParams(cutoff) })
}

export function getMetrics(
  start: string,
  end: string,
  cutoff: string,
): Promise<MetricsResponse> {
  return get('metrics', { start, end, ...cutoffParams(cutoff) })
}

export function getHorizon(
  start: string,
  end: string,
  cutoff: string,
): Promise<{ buckets: HorizonBucket[] }> {
  return get('metrics/by-horizon', { start, end, ...cutoffParams(cutoff) })
}
