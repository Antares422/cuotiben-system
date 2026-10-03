import { describe, expect, it } from 'vitest'
import { subjectColor } from '../src/subject-color'

describe('subjectColor', () => {
  it('always gives the same subject the same color', () => {
    expect(subjectColor(3)).toBe(subjectColor(3))
  })

  it('gives each of the nine default subjects its own color', () => {
    const colors = new Set(Array.from({ length: 9 }, (_, i) => subjectColor(i + 1)))

    expect(colors.size).toBe(9)
  })

  it('wraps around for subjects the user added later instead of failing', () => {
    expect(subjectColor(10)).toMatch(/^#[0-9a-f]{6}$/i)
    expect(subjectColor(10_000)).toMatch(/^#[0-9a-f]{6}$/i)
  })
})
