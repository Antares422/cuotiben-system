import type { LocationQuery } from 'vue-router'

/** 列表页的筛选状态；空值表示"不限"。 */
export interface FilterState {
  subject_id?: number
  tags: string[]
  mastery_min?: number
  mastery_max?: number
  q?: string
}

export const EMPTY_FILTERS: FilterState = { tags: [] }

function asArray(value: LocationQuery[string]): string[] {
  if (Array.isArray(value)) return value.filter((v): v is string => typeof v === 'string')
  return typeof value === 'string' ? [value] : []
}

/** 掌握程度只允许 1~5 的整数，其他值一律回退为"不限"。 */
function parseLevel(value: string | undefined): number | undefined {
  if (!value) return undefined
  const n = Number(value)
  return Number.isInteger(n) && n >= 1 && n <= 5 ? n : undefined
}

/** 从页面地址还原筛选条件（刷新、从详情返回时都靠它）。 */
export function filtersFromQuery(query: LocationQuery): FilterState {
  const filters: FilterState = { tags: [...new Set(asArray(query.tag).filter(Boolean))] }

  const subjectId = asArray(query.subject_id)[0]
  const id = subjectId ? Number(subjectId) : NaN
  if (Number.isInteger(id) && id > 0) filters.subject_id = id

  const min = parseLevel(asArray(query.mastery_min)[0])
  if (min != null) filters.mastery_min = min
  const max = parseLevel(asArray(query.mastery_max)[0])
  if (max != null) filters.mastery_max = max

  const q = (asArray(query.q)[0] ?? '').trim()
  if (q) filters.q = q

  return filters
}

/** 把筛选状态写进页面地址；空值不写入，多标签用重复 tag 参数。 */
export function queryFromFilters(filters: FilterState): Record<string, string | string[]> {
  const query: Record<string, string | string[]> = {}
  if (filters.subject_id != null) query.subject_id = String(filters.subject_id)
  if (filters.tags.length > 0) query.tag = [...filters.tags]
  if (filters.mastery_min != null) query.mastery_min = String(filters.mastery_min)
  if (filters.mastery_max != null) query.mastery_max = String(filters.mastery_max)
  if (filters.q) query.q = filters.q
  return query
}

export function hasActiveFilters(filters: FilterState): boolean {
  return (
    filters.subject_id != null ||
    filters.tags.length > 0 ||
    filters.mastery_min != null ||
    filters.mastery_max != null ||
    Boolean(filters.q)
  )
}
