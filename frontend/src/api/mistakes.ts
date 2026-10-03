import { request } from './client'
import type { Mistake, MistakeInput, Page, Subject, UploadResult } from './types'

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

export function listMistakes(page = 1, pageSize = 20): Promise<Page<Mistake>> {
  return request<Page<Mistake>>(`/api/mistakes?page=${page}&page_size=${pageSize}`)
}

export function getMistake(id: number): Promise<Mistake> {
  return request<Mistake>(`/api/mistakes/${id}`)
}

export async function listSubjects(): Promise<Subject[]> {
  const { items } = await request<{ items: Subject[] }>('/api/subjects')
  return items
}
