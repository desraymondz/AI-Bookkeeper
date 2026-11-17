import { HttpResponse, http } from 'msw'
import { describe, expect, it, vi } from 'vitest'
import { z } from 'zod'
import { server } from '@/test/server'
import { ApiError, apiFetch } from './api'

describe('apiFetch', () => {
  it('calls same-origin /api with credentials and parses with a schema', async () => {
    server.use(http.get('*/api/ping', () => HttpResponse.json({ ok: true })))
    const fetchSpy = vi.spyOn(globalThis, 'fetch')
    const data = await apiFetch('/ping', { schema: z.object({ ok: z.boolean() }) })
    expect(data).toEqual({ ok: true })
    expect(fetchSpy).toHaveBeenCalledWith(
      '/api/ping',
      expect.objectContaining({ credentials: 'include' }),
    )
    fetchSpy.mockRestore()
  })

  it('throws ApiError with status and detail on failure', async () => {
    server.use(
      http.get('*/api/broken', () => HttpResponse.json({ detail: 'Not allowed' }, { status: 403 })),
    )
    const error = await apiFetch('/broken').catch((caught: unknown) => caught)
    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({ status: 403, message: 'Not allowed' })
  })
})
