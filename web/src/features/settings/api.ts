import { type QueryClient, queryOptions, useQuery } from '@tanstack/react-query'
import { z } from 'zod'
import { apiFetch } from '@/lib/api'
import { queryKeys } from '@/lib/query'

// See api/src/bookkeeper/web_api/settings.py
export const settingsDataSchema = z.object({
  name: z.string(),
  currency: z.string(),
  timezone: z.string(),
  fy_start_month: z.number(),
  gst_registered: z.boolean(),
  gst_rate: z.union([z.string(), z.number()]),
  price_rule: z.string(),
  dup_window_days: z.number(),
  reminder_days: z.number(),
  recap_time: z.string(),
  report_day: z.number(),
  report_time: z.string(),
})

export type SettingsData = z.infer<typeof settingsDataSchema>

export const settingsStateSchema = z.object({
  configured: z.boolean(),
  settings: settingsDataSchema.nullable(),
  defaults: settingsDataSchema,
})

export type SettingsState = z.infer<typeof settingsStateSchema>

export const settingsQuery = queryOptions({
  queryKey: ['settings'] as const,
  queryFn: () => apiFetch('/settings', { schema: settingsStateSchema }),
})

export function useSettings() {
  return useQuery(settingsQuery)
}

export type SettingsPayload = {
  name: string
  currency: string
  timezone: string
  fy_start_month: number
  gst_registered: boolean
  gst_rate: string
  price_rule: string
  dup_window_days: number
  reminder_days: number
  recap_time: string
  report_day: number
  report_time: string
}

export async function saveSettings(queryClient: QueryClient, payload: SettingsPayload) {
  const saved = await apiFetch('/settings', {
    method: 'PUT',
    body: payload,
    schema: settingsDataSchema,
  })
  queryClient.setQueryData(settingsQuery.queryKey, (previous) => ({
    configured: true,
    settings: saved,
    defaults: previous?.defaults ?? saved,
  }))
  await queryClient.invalidateQueries({ queryKey: queryKeys.config })
  await queryClient.invalidateQueries({ queryKey: ['accounts'] })
  return saved
}
