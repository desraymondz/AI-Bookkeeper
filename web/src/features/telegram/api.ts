import { type QueryClient, queryOptions, useQuery } from '@tanstack/react-query'
import { z } from 'zod'
import { apiFetch } from '@/lib/api'

// See api/src/bookkeeper/web_api/links.py
export const linkSchema = z.object({
  token: z.string(),
  url: z.string(),
  expires_at: z.string(),
})

export type InviteLink = z.infer<typeof linkSchema>

export const bossLinkSchema = z.object({
  connected: z.boolean(),
  username: z.string().nullable(),
  display_name: z.string().nullable(),
  linked_at: z.string().nullable(),
})

export type BossLinkState = z.infer<typeof bossLinkSchema>

export const bossLinkQuery = queryOptions({
  queryKey: ['links', 'boss'] as const,
  queryFn: () => apiFetch('/links/boss', { schema: bossLinkSchema }),
})

export function useBossLink(refetchInterval: number | false) {
  return useQuery({ ...bossLinkQuery, refetchInterval })
}

export function createBossLink() {
  return apiFetch('/links/boss', { method: 'POST', schema: linkSchema })
}

export function createSupplierLink(supplierId: number) {
  return apiFetch(`/links/suppliers/${supplierId}`, { method: 'POST', schema: linkSchema })
}

export function invalidateBossLink(queryClient: QueryClient) {
  return queryClient.invalidateQueries({ queryKey: bossLinkQuery.queryKey })
}
