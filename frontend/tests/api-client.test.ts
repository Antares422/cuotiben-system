import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, errorMessage, request } from '../src/api/client'

function respondWith(status: number, body: unknown): void {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue(
      new Response(typeof body === 'string' ? body : JSON.stringify(body), { status }),
    ),
  )
}

afterEach(() => vi.unstubAllGlobals())

describe('request', () => {
  it('returns data when the envelope code is 2xx', async () => {
    respondWith(200, { code: 200, message: 'ok', data: { id: 7 } })

    expect(await request('/api/mistakes/7')).toEqual({ id: 7 })
  })

  it('throws ApiError carrying code, message and data for a failed envelope', async () => {
    const data = { fields: [{ field: 'content', message: '不能为空' }] }
    respondWith(422, { code: 422, message: '题目内容不能为空', data })

    const error = await request('/api/mistakes').catch((e) => e)

    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({ code: 422, message: '题目内容不能为空', data })
  })

  it('turns a network failure into ApiError with code 0', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))

    const error = await request('/api/mistakes').catch((e) => e)

    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({ code: 0, message: '网络连接失败，请检查网络' })
  })

  it('turns a non-JSON response such as a gateway error page into ApiError', async () => {
    respondWith(502, '<html>Bad Gateway</html>')

    const error = await request('/api/mistakes').catch((e) => e)

    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({ code: 502, message: '服务暂时不可用，请稍后再试' })
  })
})

describe('errorMessage', () => {
  it('uses the message of an ApiError', () => {
    expect(errorMessage(new ApiError(422, '题目内容不能为空'))).toBe('题目内容不能为空')
  })

  it('falls back to a generic sentence for unexpected errors, never leaking internals', () => {
    expect(errorMessage(new TypeError("Cannot read properties of undefined (reading 'id')"))).toBe(
      '出错了，请稍后重试',
    )
    expect(errorMessage('boom')).toBe('出错了，请稍后重试')
  })
})
