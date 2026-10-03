import { vi } from 'vitest'

export interface RecordedRequest {
  method: string
  url: string
  body: unknown
}

interface FakeResponse {
  status?: number
  message?: string
  data?: unknown
}

type Handler = (request: RecordedRequest) => FakeResponse | Promise<FakeResponse>

/** 在 fetch 这一层伪造后端：键是 "METHOD /path"（不含查询串），返回信封格式的响应。 */
export function installFakeBackend(routes: Record<string, Handler>) {
  const calls: RecordedRequest[] = []

  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, init?: RequestInit) => {
      const method = init?.method ?? 'GET'
      const body = typeof init?.body === 'string' ? JSON.parse(init.body) : init?.body
      const request = { method, url, body }
      calls.push(request)

      const handler = routes[`${method} ${url.split('?')[0]}`]
      const { status = 200, message = status < 300 ? 'ok' : 'error', data = null } = handler
        ? await handler(request)
        : { status: 404, message: '资源不存在' }
      return new Response(JSON.stringify({ code: status, message, data }), { status })
    }),
  )

  return { calls }
}
