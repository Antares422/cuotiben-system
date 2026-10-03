import { afterEach, describe, expect, it, vi } from 'vitest'
import { createMistake, getMistake, listMistakes, listSubjects, uploadImage } from '../src/api/mistakes'

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
    const page = { items: [], total: 0, page: 2, page_size: 10 }
    const fetchMock = stubFetch(page)

    expect(await listMistakes(2, 10)).toEqual(page)

    expect(fetchMock.mock.calls[0][0]).toBe('/api/mistakes?page=2&page_size=10')
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
