import { describe, expect, it } from 'vitest'
import { comparisonToCsv } from './csv'
import type { ComparisonPoint } from '../api/client'

const point: ComparisonPoint = {
  start_time: '2026-01-01T00:00:00Z',
  actual_mw: 100,
  forecast_mw: 110,
  publish_time: '2025-12-31T09:00:00Z',
  horizon_hours: 15,
  error_mw: 10,
  abs_error_mw: 10,
}

describe('comparisonToCsv', () => {
  it('writes a header and one comparison row', () => {
    const csv = comparisonToCsv([point]).split('\r\n')
    expect(csv).toHaveLength(2)
    expect(csv[0]).toContain('start_time_utc')
    expect(csv[1]).toContain('"110"')
    expect(csv[1]).toContain('"10"')
  })

  it('preserves gaps as empty cells', () => {
    const csv = comparisonToCsv([{ ...point, actual_mw: null, error_mw: null }])
    expect(csv).toContain('"2026-01-01T00:00:00Z","","110"')
  })

  it('escapes quotes in string values', () => {
    const csv = comparisonToCsv([{ ...point, publish_time: 'a"b' }])
    expect(csv).toContain('"a""b"')
  })
})
