import type { z } from 'zod'

export const API_BASE = '/api'

export class ApiError extends Error {
  readonly status: number
  readonly body: unknown

  constructor(status: number, message: string, body: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.body = body
  }
}

type ApiFetchOptions<T> = Omit<RequestInit, 'body'> & {
  body?: unknown
  schema?: z.ZodType<T>
}

async function readBody(response: Response): Promise<unknown> {
  if (response.status === 204) return null
  const type = response.headers.get('content-type') ?? ''
  if (type.includes('application/json')) return response.json()
  return response.text()
}

export async function apiFetch<T = unknown>(
  path: string,
  { body, schema, headers, ...init }: ApiFetchOptions<T> = {},
): Promise<T> {
  const finalHeaders = new Headers(headers)
  finalHeaders.set('Accept', 'application/json')
  let payload: BodyInit | undefined
  if (body instanceof FormData) {
    payload = body
  } else if (body !== undefined) {
    finalHeaders.set('Content-Type', 'application/json')
    payload = JSON.stringify(body)
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: finalHeaders,
    body: payload,
    credentials: 'include',
  })
  const data = await readBody(response)

  if (!response.ok) {
    const detail =
      data && typeof data === 'object' && 'detail' in data && typeof data.detail === 'string'
        ? data.detail
        : response.statusText || `Request failed with status ${response.status}`
    throw new ApiError(response.status, detail, data)
  }

  return schema ? schema.parse(data) : (data as T)
}
