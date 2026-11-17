import { type QueryClient, queryOptions, useQuery } from '@tanstack/react-query'
import { z } from 'zod'
import { apiFetch } from '@/lib/api'

// See api/src/bookkeeper/web_api/accounts.py
export const ACCOUNT_TYPES = [
  { value: 'asset', label: 'Asset' },
  { value: 'liability', label: 'Liability' },
  { value: 'equity', label: 'Equity' },
  { value: 'revenue', label: 'Revenue' },
  { value: 'expense', label: 'Expense' },
  { value: 'contra_asset', label: 'Contra-asset' },
] as const

export const accountSchema = z.object({
  id: z.number(),
  code: z.string(),
  name: z.string(),
  type: z.string(),
  subtype: z.string().nullable(),
  active: z.boolean(),
  has_postings: z.boolean(),
})

export type Account = z.infer<typeof accountSchema>

export const accountsQuery = queryOptions({
  queryKey: ['accounts'] as const,
  queryFn: () => apiFetch('/accounts', { schema: z.array(accountSchema) }),
})

export function useAccounts() {
  return useQuery(accountsQuery)
}

export function typeLabel(type: string) {
  return ACCOUNT_TYPES.find((item) => item.value === type)?.label ?? type
}

export function createAccount(
  queryClient: QueryClient,
  body: { code: string; name: string; type: string },
) {
  return apiFetch('/accounts', { method: 'POST', body, schema: accountSchema }).then(
    async (account) => {
      await queryClient.invalidateQueries({ queryKey: accountsQuery.queryKey })
      return account
    },
  )
}

export function setAccountActive(queryClient: QueryClient, id: number, active: boolean) {
  return apiFetch(`/accounts/${id}`, {
    method: 'PATCH',
    body: { active },
    schema: accountSchema,
  }).then(async (account) => {
    await queryClient.invalidateQueries({ queryKey: accountsQuery.queryKey })
    return account
  })
}
