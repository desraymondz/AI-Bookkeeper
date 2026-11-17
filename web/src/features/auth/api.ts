import { type QueryClient, queryOptions, useQuery } from '@tanstack/react-query'
import { redirect } from '@tanstack/react-router'
import { z } from 'zod'
import { ApiError, apiFetch } from '@/lib/api'

// See planning/01-prd.md#F-001
export const meSchema = z.object({ email: z.string() })
export type Me = z.infer<typeof meSchema>

export const meQuery = queryOptions({
  queryKey: ['auth', 'me'] as const,
  queryFn: () => apiFetch('/auth/me', { schema: meSchema }),
  retry: false,
})

export function useMe() {
  return useQuery(meQuery)
}

export async function readSession(queryClient: QueryClient): Promise<Me | null> {
  try {
    return await queryClient.fetchQuery(meQuery)
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) return null
    throw error
  }
}

export async function requireSession(queryClient: QueryClient): Promise<Me> {
  const me = await readSession(queryClient)
  if (!me) throw redirect({ to: '/sign-in' })
  return me
}

export function logout() {
  return apiFetch<null>('/auth/logout', { method: 'POST' })
}

export const GOOGLE_LOGIN_URL = '/api/auth/login'
