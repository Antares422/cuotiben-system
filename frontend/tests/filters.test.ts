import { describe, expect, it } from 'vitest'
import { filtersFromQuery, hasActiveFilters, queryFromFilters } from '../src/filters'

describe('filtersFromQuery', () => {
  it('turns an empty query into an empty filter state', () => {
    expect(filtersFromQuery({})).toEqual({ tags: [] })
  })

  it('reads subject, tags, mastery range and keyword', () => {
    const filters = filtersFromQuery({
      subject_id: '2',
      tag: ['函数', '最值'],
      mastery_min: '2',
      mastery_max: '4',
      q: '二次函数',
    })
    expect(filters).toEqual({
      subject_id: 2,
      tags: ['函数', '最值'],
      mastery_min: 2,
      mastery_max: 4,
      q: '二次函数',
    })
  })

  it('accepts a single tag string as well as repeated ones', () => {
    expect(filtersFromQuery({ tag: '函数' }).tags).toEqual(['函数'])
    expect(filtersFromQuery({ tag: ['a', 'b', 'a'] }).tags).toEqual(['a', 'b'])
  })

  it.each(['0', '6', 'abc', '2.5', ''])('falls back to unlimited for invalid mastery value %j', (value) => {
    expect(filtersFromQuery({ mastery_min: value })).toEqual({ tags: [] })
    expect(filtersFromQuery({ mastery_max: value })).toEqual({ tags: [] })
  })

  it('drops an invalid subject id and blank keyword', () => {
    expect(filtersFromQuery({ subject_id: 'abc' })).toEqual({ tags: [] })
    expect(filtersFromQuery({ subject_id: '0' })).toEqual({ tags: [] })
    expect(filtersFromQuery({ q: '   ' })).toEqual({ tags: [] })
  })
})

describe('queryFromFilters', () => {
  it('writes nothing for an empty state', () => {
    expect(queryFromFilters({ tags: [] })).toEqual({})
  })

  it('writes each tag as a repeated tag parameter', () => {
    expect(queryFromFilters({ tags: ['函数', '最值'] })).toEqual({ tag: ['函数', '最值'] })
  })

  it('writes only the values that are set', () => {
    expect(queryFromFilters({ tags: [], subject_id: 2, mastery_min: 3, q: 'abc' })).toEqual({
      subject_id: '2',
      mastery_min: '3',
      q: 'abc',
    })
  })
})

describe('round trip', () => {
  it('query → filters → query keeps every condition', () => {
    const query = { subject_id: '2', tag: ['函数'], mastery_min: '2', mastery_max: '5', q: 'x' }
    expect(queryFromFilters(filtersFromQuery(query))).toEqual({
      subject_id: '2',
      tag: ['函数'],
      mastery_min: '2',
      mastery_max: '5',
      q: 'x',
    })
  })
})

describe('hasActiveFilters', () => {
  it('is false for the empty state and true otherwise', () => {
    expect(hasActiveFilters({ tags: [] })).toBe(false)
    expect(hasActiveFilters({ tags: ['函数'] })).toBe(true)
    expect(hasActiveFilters({ tags: [], mastery_min: 1 })).toBe(true)
    expect(hasActiveFilters({ tags: [], q: 'x' })).toBe(true)
    expect(hasActiveFilters({ tags: [], subject_id: 1 })).toBe(true)
  })
})
