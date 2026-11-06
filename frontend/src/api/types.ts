export interface Subject {
  id: number
  name: string
  mistake_count?: number
}

export interface Tag {
  id: number
  name: string
  mistake_count: number
}

export interface OcrDraft {
  status: 'ok' | 'empty' | 'failed'
  text: string
  message: string | null
}

export interface UploadResult {
  image_id: string
  image_url: string
  ocr: OcrDraft
}

export interface Mistake {
  id: number
  content: string
  answer: string | null
  error_reason: string | null
  subject: Subject
  tags: string[]
  image_id: string | null
  image_url: string | null
  mastery_level: number
  mastered_at: string | null
  created_at: string
  updated_at: string
}

export interface MistakeInput {
  content: string
  subject_id: number
  answer?: string | null
  error_reason?: string | null
  tags?: string[]
  image_id?: string | null
}

export interface Page<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  /** 不受筛选影响的错题总数，容量提醒用 */
  overall_total: number
}
