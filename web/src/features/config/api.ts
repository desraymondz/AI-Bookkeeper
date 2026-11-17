import { queryOptions, useQuery } from '@tanstack/react-query'
import { z } from 'zod'
import { apiFetch } from '@/lib/api'
import { queryKeys } from '@/lib/query'

export const appConfigSchema = z.object({
  bot_username: z.string().min(1).nullable(),
  business_name: z.string().nullable().optional(),
})

export type AppConfig = z.infer<typeof appConfigSchema>

export const appConfigQuery = queryOptions({
  queryKey: queryKeys.config,
  queryFn: () => apiFetch('/config', { schema: appConfigSchema }),
  staleTime: Number.POSITIVE_INFINITY,
})

export function useAppConfig() {
  return useQuery(appConfigQuery)
}

export function telegramBotUrl(botUsername: string) {
  return `https://t.me/${encodeURIComponent(botUsername.replace(/^@/, ''))}`
}
