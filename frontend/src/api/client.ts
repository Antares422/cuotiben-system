export class ApiError extends Error {
  constructor(
    public code: number,
    message: string,
    public data: unknown = null,
  ) {
    super(message)
  }
}

interface Envelope<T> {
  code: number
  message: string
  data: T
}

/** 所有网络请求的唯一出口：成功返回 data，失败一律抛 ApiError。 */
export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(path, init)
  } catch {
    throw new ApiError(0, '网络连接失败，请检查网络')
  }

  let envelope: Envelope<T>
  try {
    envelope = (await response.json()) as Envelope<T>
  } catch {
    // 网关、代理返回的不是 JSON（如 502 页面）
    throw new ApiError(response.status, '服务暂时不可用，请稍后再试')
  }
  if (envelope.code < 200 || envelope.code >= 300) {
    throw new ApiError(envelope.code, envelope.message, envelope.data)
  }
  return envelope.data
}

/** 把任何异常变成可以直接展示给用户的一句话。 */
export function errorMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : '出错了，请稍后重试'
}
