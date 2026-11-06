import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  createMistake,
  createSubject,
  deleteMistake,
  deleteSubject,
  deleteTag,
  getMistake,
  listMistakes,
  listSubjects,
  listTags,
  setMastery,
  updateMistake,
  updateSubject,
  updateTag,
  uploadImage,
} from '../src/api/mistakes'
import type { Page } from '../src/api/types'

function urlOf(fetchMock: ReturnType<typeof stubFetch>) {
  return new URL(fetchMock.mock.calls[0][0] as string, 'http://test')
}

function stubFetch(data: unknown, status = 200) {
  const fetchMock = vi
    .fn()
    .mockResolvedValue(new Response(JSON.stringify({ code: status, message: 'ok', data })))
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

afterEach(() => vi.unstubAllGlobals())

describe('uploadImage', () => {
  it('posts the file as multipart form data to /api/uploads', async () => {
    const result = { image_id: 'abc', image_url: '/api/images/abc', ocr: { status: 'ok', text: '题', message: null } }
    const fetchMock = stubFetch(result, 201)
    const file = new File(['bytes'], 'q.png', { type: 'image/png' })

    expect(await uploadImage(file)).toEqual(result)

    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/uploads')
    expect(init.method).toBe('POST')
    expect((init.body as FormData).get('file')).toBeInstanceOf(File)
    // 不能手动设置 Content-Type，否则浏览器不会带上 multipart 的 boundary
    expect(init.headers).toBeUndefined()
  })
})

describe('createMistake', () => {
  it('posts the input as JSON to /api/mistakes', async () => {
    const saved = { id: 1, content: '题' }
    const fetchMock = stubFetch(saved, 201)

    expect(await createMistake({ content: '题', subject_id: 2, tags: ['函数'] })).toEqual(saved)

    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/mistakes')
    expect(init.method).toBe('POST')
    expect(init.headers).toEqual({ 'Content-Type': 'application/json' })
    expect(JSON.parse(init.body)).toEqual({ content: '题', subject_id: 2, tags: ['函数'] })
  })
})

describe('listMistakes', () => {
  it('passes page and page_size as query parameters', async () => {
    const page: Page<unknown> = { items: [], total: 0, page: 2, page_size: 10, overall_total: 10 }
    const fetchMock = stubFetch(page)

    expect(await listMistakes({ page: 2, page_size: 10 })).toEqual(page)

    expect(fetchMock.mock.calls[0][0]).toBe('/api/mistakes?page=2&page_size=10')
  })

  it('requests the first page of twenty by default', async () => {
    const fetchMock = stubFetch({ items: [], total: 0, page: 1, page_size: 20, overall_total: 0 })

    await listMistakes()

    expect(fetchMock.mock.calls[0][0]).toBe('/api/mistakes?page=1&page_size=20')
  })

  it('combines every filter into the query string', async () => {
    const fetchMock = stubFetch({ items: [], total: 0, page: 1, page_size: 20, overall_total: 7 })

    await listMistakes({
      page: 1,
      page_size: 20,
      subject_id: 2,
      tags: ['函数', '最值'],
      mastery_min: 2,
      mastery_max: 4,
      q: '二次 函数',
    })

    const url = urlOf(fetchMock)
    expect(url.searchParams.get('page')).toBe('1')
    expect(url.searchParams.get('page_size')).toBe('20')
    expect(url.searchParams.get('subject_id')).toBe('2')
    expect(url.searchParams.getAll('tag')).toEqual(['函数', '最值'])
    expect(url.searchParams.get('mastery_min')).toBe('2')
    expect(url.searchParams.get('mastery_max')).toBe('4')
    expect(url.searchParams.get('q')).toBe('二次 函数')
  })

  it('omits filters that are not set', async () => {
    const fetchMock = stubFetch({ items: [], total: 0, page: 1, page_size: 20, overall_total: 0 })

    await listMistakes({ page: 1, page_size: 20, subject_id: 3 })

    const url = urlOf(fetchMock)
    expect(url.searchParams.get('subject_id')).toBe('3')
    expect(url.searchParams.getAll('tag')).toEqual([])
    expect(url.searchParams.get('mastery_min')).toBeNull()
    expect(url.searchParams.get('q')).toBeNull()
  })
})

describe('listTags', () => {
  it('returns the items array of /api/tags', async () => {
    const fetchMock = stubFetch({ items: [{ id: 1, name: '函数', mistake_count: 8 }] })

    expect(await listTags()).toEqual([{ id: 1, name: '函数', mistake_count: 8 }])

    expect(fetchMock.mock.calls[0][0]).toBe('/api/tags')
  })
})

describe('setMastery', () => {
  it('puts the level to /api/mistakes/{id}/mastery', async () => {
    const updated = { id: 7, mastery_level: 4 }
    const fetchMock = stubFetch(updated)

    expect(await setMastery(7, 4)).toEqual(updated)

    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/mistakes/7/mastery')
    expect(init.method).toBe('PUT')
    expect(init.headers).toEqual({ 'Content-Type': 'application/json' })
    expect(JSON.parse(init.body)).toEqual({ level: 4 })
  })
})

describe('updateMistake', () => {
  it('patches the input as JSON to /api/mistakes/{id}', async () => {
    const updated = { id: 7 }
    const fetchMock = stubFetch(updated)
    const input = { content: '改后', subject_id: 1, tags: ['函数'] }

    expect(await updateMistake(7, input)).toEqual(updated)

    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/mistakes/7')
    expect(init.method).toBe('PATCH')
    expect(init.headers).toEqual({ 'Content-Type': 'application/json' })
    expect(JSON.parse(init.body)).toEqual(input)
  })
})

describe('deleteMistake', () => {
  it('deletes /api/mistakes/{id} and resolves with null data', async () => {
    const fetchMock = stubFetch(null)

    expect(await deleteMistake(7)).toBeNull()

    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/mistakes/7')
    expect(init.method).toBe('DELETE')
  })
})

describe('subject management', () => {
  it('creates a subject with a JSON name', async () => {
    const created = { id: 3, name: '物理', mistake_count: 0 }
    const fetchMock = stubFetch(created, 201)

    expect(await createSubject('物理')).toEqual(created)

    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/subjects')
    expect(init.method).toBe('POST')
    expect(JSON.parse(init.body)).toEqual({ name: '物理' })
  })

  it('renames a subject', async () => {
    const fetchMock = stubFetch({ id: 3, name: '高中物理', mistake_count: 2 })

    expect(await updateSubject(3, '高中物理')).toEqual({ id: 3, name: '高中物理', mistake_count: 2 })

    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/subjects/3')
    expect(init.method).toBe('PATCH')
    expect(JSON.parse(init.body)).toEqual({ name: '高中物理' })
  })

  it('deletes a subject', async () => {
    const fetchMock = stubFetch(null)

    expect(await deleteSubject(3)).toBeNull()

    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/subjects/3')
    expect(init.method).toBe('DELETE')
  })
})

describe('tag management', () => {
  it('renames a tag', async () => {
    const fetchMock = stubFetch({ id: 5, name: '函数与方程', mistake_count: 8 })

    expect(await updateTag(5, '函数与方程')).toEqual({ id: 5, name: '函数与方程', mistake_count: 8 })

    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/tags/5')
    expect(init.method).toBe('PATCH')
    expect(JSON.parse(init.body)).toEqual({ name: '函数与方程' })
  })

  it('deletes a tag', async () => {
    const fetchMock = stubFetch(null)

    expect(await deleteTag(5)).toBeNull()

    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/tags/5')
    expect(init.method).toBe('DELETE')
  })
})

describe('getMistake', () => {
  it('requests /api/mistakes/{id}', async () => {
    const fetchMock = stubFetch({ id: 7 })

    expect(await getMistake(7)).toEqual({ id: 7 })

    expect(fetchMock.mock.calls[0][0]).toBe('/api/mistakes/7')
  })
})

describe('listSubjects', () => {
  it('returns the items array of /api/subjects', async () => {
    const fetchMock = stubFetch({ items: [{ id: 1, name: '语文' }] })

    expect(await listSubjects()).toEqual([{ id: 1, name: '语文' }])

    expect(fetchMock.mock.calls[0][0]).toBe('/api/subjects')
  })
})
