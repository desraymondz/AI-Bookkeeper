import { type QueryClient, queryOptions, useQuery } from '@tanstack/react-query'
import { z } from 'zod'
import { apiFetch } from '@/lib/api'

// See api/src/bookkeeper/web_api/users.py
export const userSchema = z.object({
  id: z.number(),
  display_name: z.string().nullable(),
  username: z.string().nullable(),
  role: z.enum(['boss', 'supplier']),
  supplier_id: z.number().nullable(),
  supplier_name: z.string().nullable(),
  status: z.enum(['active', 'deactivated', 'blocked']),
  linked_at: z.string().nullable(),
})

export type AppUser = z.infer<typeof userSchema>

export const usersQuery = queryOptions({
  queryKey: ['users'] as const,
  queryFn: () => apiFetch('/users', { schema: z.array(userSchema) }),
})

export function useUsers() {
  return useQuery(usersQuery)
}

export function updateUser(
  queryClient: QueryClient,
  id: number,
  body: { supplier_id?: number; status?: AppUser['status'] },
) {
  return apiFetch(`/users/${id}`, { method: 'PATCH', body, schema: userSchema }).then(
    async (user) => {
      await queryClient.invalidateQueries({ queryKey: usersQuery.queryKey })
      return user
    },
  )
}

// A revoked user drops out of the list API, so the row is kept in the cache with its new status.
export function revokeUser(queryClient: QueryClient, id: number) {
  return apiFetch(`/users/${id}/revoke`, { method: 'POST', schema: userSchema }).then((user) => {
    queryClient.setQueryData<AppUser[]>(usersQuery.queryKey, (rows) =>
      (rows ?? []).map((row) => (row.id === user.id ? user : row)),
    )
    return user
  })
}
