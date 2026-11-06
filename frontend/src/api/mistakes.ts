import { request } from './client'
import type { Mistake, MistakeInput, Page, Subject, Tag, UploadResult } from './types'

export function uploadImage(file: File): Promise<UploadResult> {
  const body = new FormData()
  body.append('file', file)
  // 不手动设置 Content-Type：浏览器会自动带上 multipart 的 boundary
  return request<UploadResult>('/api/uploads', { method: 'POST', body })
}

export function createMistake(input: MistakeInput): Promise<Mistake> {
  return request<Mistake>('/api/mistakes', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  })
}

export interface MistakeQuery {
  page?: number
  page_size?: number
  subject_id?: number
  tags?: string[]
  mastery_min?: number
  mastery_max?: number
  q?: string
}

export function listMistakes(query: MistakeQuery = {}): Promise<Page<Mistake>> {
  const params = new URLSearchParams()
  params.set('page', String(query.page ?? 1))
  params.set('page_size', String(query.page_size ?? 20))
  if (query.subject_id != null) params.set('subject_id', String(query.subject_id))
  for (const tag of query.tags ?? []) params.append('tag', tag)
  if (query.mastery_min != null) params.set('mastery_min', String(query.mastery_min))
  if (query.mastery_max != null) params.set('mastery_max', String(query.mastery_max))
  if (query.q) params.set('q', query.q)
  return request<Page<Mistake>>(`/api/mistakes?${params.toString()}`)
}

export function getMistake(id: number): Promise<Mistake> {
  return request<Mistake>(`/api/mistakes/${id}`)
}

export function setMastery(id: number, level: number): Promise<Mistake> {
  return request<Mistake>(`/api/mistakes/${id}/mastery`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ level }),
  })
}

export function updateMistake(id: number, input: MistakeInput): Promise<Mistake> {
  return request<Mistake>(`/api/mistakes/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  })
}

export function deleteMistake(id: number): Promise<null> {
  return request<null>(`/api/mistakes/${id}`, { method: 'DELETE' })
}

export async function listSubjects(): Promise<Subject[]> {
  const { items } = await request<{ items: Subject[] }>('/api/subjects')
  return items
}

export function createSubject(name: string): Promise<Subject> {
  return request<Subject>('/api/subjects', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  })
}

export function updateSubject(id: number, name: string): Promise<Subject> {
  return request<Subject>(`/api/subjects/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  })
}

export function deleteSubject(id: number): Promise<null> {
  return request<null>(`/api/subjects/${id}`, { method: 'DELETE' })
}

export async function listTags(): Promise<Tag[]> {
  const { items } = await request<{ items: Tag[] }>('/api/tags')
  return items
}

export function updateTag(id: number, name: string): Promise<Tag> {
  return request<Tag>(`/api/tags/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  })
}

export function deleteTag(id: number): Promise<null> {
  return request<null>(`/api/tags/${id}`, { method: 'DELETE' })
}
