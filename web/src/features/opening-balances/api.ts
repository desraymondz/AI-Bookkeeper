import { type QueryClient, queryOptions, useQuery } from '@tanstack/react-query'
import { z } from 'zod'
import { apiFetch } from '@/lib/api'

// See api/src/bookkeeper/web_api/opening_balances.py
const lineSchema = z.object({ account_id: z.number(), debit: z.string(), credit: z.string() })

const stateSchema = z.object({
  entry_no: z.string().nullable(),
  as_at: z.string().nullable(),
  lines: z.array(lineSchema),
})

const savedSchema = z.object({
  entry_no: z.string(),
  as_at: z.string(),
  reversed_entry_no: z.string().nullable(),
  reversal_entry_no: z.string().nullable(),
})

export type OpeningState = z.infer<typeof stateSchema>
export type OpeningLine = z.infer<typeof lineSchema>

export const openingQuery = queryOptions({
  queryKey: ['opening-balances'] as const,
  queryFn: () => apiFetch('/opening-balances', { schema: stateSchema }),
})

export function useOpening() {
  return useQuery(openingQuery)
}

export function saveOpening(
  queryClient: QueryClient,
  body: { as_at: string; lines: OpeningLine[] },
) {
  return apiFetch('/opening-balances', { method: 'PUT', body, schema: savedSchema }).then(
    async (saved) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: openingQuery.queryKey }),
        queryClient.invalidateQueries({ queryKey: ['journal'] }),
        queryClient.invalidateQueries({ queryKey: ['accounts'] }),
      ])
      return saved
    },
  )
}

const AMOUNT = /^\d{1,12}(\.\d{0,2})?$/

export function parseCents(text: string): bigint | null {
  const value = text.trim().replace(/,/g, '')
  if (value === '') return 0n
  if (!AMOUNT.test(value)) return null
  const [whole = '0', fraction = ''] = value.split('.')
  return BigInt(whole) * 100n + BigInt(`${fraction}00`.slice(0, 2))
}

export function centsToText(cents: bigint): string {
  const negative = cents < 0n
  const abs = negative ? -cents : cents
  const whole = (abs / 100n).toString()
  const fraction = (abs % 100n).toString().padStart(2, '0')
  return `${negative ? '-' : ''}${whole}.${fraction}`
}
