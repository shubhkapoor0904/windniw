import { describe, expect, it } from 'vitest'
import { formatLocalTime, formatMetric, formatMw } from './formatters'

describe('dashboard formatters', () => {
  it('shows missing metrics explicitly', () => {
    expect(formatMetric(null)).toBe('—')
    expect(formatMw(undefined)).toBe('—')
  })

  it('formats MW and metric values for the UK locale', () => {
    expect(formatMw(12345)).toBe('12,345 MW')
    expect(formatMetric(12.345, 1)).toBe('12.3')
  })

  it('formats delivery slots in Europe/London time', () => {
    expect(formatLocalTime('2026-01-01T09:30:00Z')).toBe('09:30')
  })
})
