import { type QueryClient, queryOptions, useQuery } from '@tanstack/react-query'
import { z } from 'zod'
import { apiFetch } from '@/lib/api'

// See api/src/bookkeeper/web_api/suppliers.py
export const supplierSchema = z.object({
  id: z.number(),
  name: z.string(),
  uen: z.string().nullable(),
  default_account_id: z.number(),
  default_account_name: z.string(),
  terms_days: z.number(),
  telegram_username_hint: z.string().nullable(),
  active: z.boolean(),
  created_at: z.string(),
})

export type Supplier = z.infer<typeof supplierSchema>

export type SupplierInput = {
  name: string
  default_account_id: number
  uen: string
  terms_days: number
  telegram_username_hint: string
}

export const suppliersQuery = queryOptions({
  queryKey: ['suppliers'] as const,
  queryFn: () => apiFetch('/suppliers', { schema: z.array(supplierSchema) }),
})

export function useSuppliers() {
  return useQuery(suppliersQuery)
}

async function refresh(queryClient: QueryClient) {
  await queryClient.invalidateQueries({ queryKey: suppliersQuery.queryKey })
  await queryClient.invalidateQueries({ queryKey: ['users'] })
}

export function createSupplier(queryClient: QueryClient, body: SupplierInput) {
  return apiFetch('/suppliers', { method: 'POST', body, schema: supplierSchema }).then(
    async (supplier) => {
      await refresh(queryClient)
      return supplier
    },
  )
}

export function updateSupplier(
  queryClient: QueryClient,
  id: number,
  body: Partial<SupplierInput> & { active?: boolean },
) {
  return apiFetch(`/suppliers/${id}`, { method: 'PATCH', body, schema: supplierSchema }).then(
    async (supplier) => {
      await refresh(queryClient)
      return supplier
    },
  )
}
