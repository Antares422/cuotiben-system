import { describe, expect, it } from 'vitest'
import { formatDateTime } from '../src/format'

describe('formatDateTime', () => {
  it.each([
    ['Asia/Shanghai', '2026-10-03 16:30'],
    ['UTC', '2026-10-03 08:30'],
    ['America/Los_Angeles', '2026-10-03 01:30'],
  ])('renders a UTC timestamp in %s as %s', (timeZone, expected) => {
    expect(formatDateTime('2026-10-03T08:30:00Z', timeZone)).toBe(expected)
  })

  it('accepts fractional seconds as returned by the server', () => {
    expect(formatDateTime('2026-10-03T08:30:00.030246Z', 'UTC')).toBe('2026-10-03 08:30')
  })
})
