import { queryOptions, useQuery } from '@tanstack/react-query'
import { z } from 'zod'
import { apiFetch } from '@/lib/api'
import type { RangeSearch } from '@/lib/search'

// See api/src/bookkeeper/reports/journal.py, trial_balance.py, statements.py

const money = z.string()

const lineSchema = z.object({
  line_no: z.number(),
  account_id: z.number(),
  account_code: z.string(),
  account_name: z.string(),
  memo: z.string().nullable(),
  debit: money,
  credit: money,
})

const entrySchema = z.object({
  id: z.number(),
  entry_no: z.string(),
  date: z.string(),
  description: z.string(),
  source: z.string(),
  kind: z.string(),
  status: z.string(),
  note: z.string().nullable(),
  lines: z.array(lineSchema),
  total_debit: money,
  total_credit: money,
})

export type JournalEntry = z.infer<typeof entrySchema>

const listingSchema = z.object({
  start: z.string(),
  end: z.string(),
  entries: z.array(entrySchema),
  total_debit: money,
  total_credit: money,
})

const linkedSchema = z.object({ id: z.number(), entry_no: z.string() }).nullable()

const detailSchema = entrySchema.extend({
  checks: z.array(
    z.object({ check_code: z.string(), passed: z.boolean(), detail: z.string().nullable() }),
  ),
  document: z
    .object({ document_id: z.number(), invoice_id: z.number(), mime: z.string(), kind: z.string() })
    .nullable(),
  audit: z.array(
    z.object({
      at: z.string(),
      actor: z.string(),
      action: z.string(),
      detail: z.record(z.string(), z.unknown()),
    }),
  ),
  reverses: linkedSchema,
  reversed_by: linkedSchema,
})

export type JournalEntryDetail = z.infer<typeof detailSchema>

const tbSchema = z.object({
  as_at: z.string(),
  rows: z.array(
    z.object({
      account_id: z.number(),
      code: z.string(),
      name: z.string(),
      type: z.string(),
      debit: money,
      credit: money,
    }),
  ),
  total_debit: money,
  total_credit: money,
  difference: money,
})

export type TrialBalance = z.infer<typeof tbSchema>

const statementLine = z.object({
  account_id: z.number().nullable(),
  code: z.string().nullable(),
  name: z.string(),
  amount: money,
})

export type StatementLine = z.infer<typeof statementLine>

const pnlSchema = z.object({
  start: z.string(),
  end: z.string(),
  revenue: z.array(statementLine),
  total_revenue: money,
  cogs: z.array(statementLine),
  total_cogs: money,
  gross_profit: money,
  operating_expenses: z.array(statementLine),
  total_operating_expenses: money,
  operating_profit: money,
  other_items: z.array(statementLine),
  total_other_items: money,
  net_profit: money,
})

export type ProfitAndLoss = z.infer<typeof pnlSchema>

const bsSchema = z.object({
  as_at: z.string(),
  current_assets: z.array(statementLine),
  total_current_assets: money,
  fixed_assets: z.array(statementLine),
  total_fixed_assets: money,
  total_assets: money,
  liabilities: z.array(statementLine),
  total_liabilities: money,
  equity: z.array(statementLine),
  total_equity: money,
  total_liabilities_and_equity: money,
  difference: money,
  balanced: z.boolean(),
})

export type BalanceSheet = z.infer<typeof bsSchema>

const API_PRESET: Record<RangeSearch['range'], string> = {
  'this-month': 'this_month',
  'last-month': 'last_month',
  'last-3-months': 'last_3_months',
  'year-to-date': 'ytd',
  'last-12-months': 'last_12_months',
  custom: 'custom',
}

export function rangeParams(search: RangeSearch): string {
  const params = new URLSearchParams()
  if (search.range === 'custom' && search.from && search.to) {
    params.set('preset', 'custom')
    params.set('start', search.from)
    params.set('end', search.to)
  } else {
    params.set('preset', API_PRESET[search.range === 'custom' ? 'this-month' : search.range])
  }
  return params.toString()
}

export function useJournal(search: RangeSearch) {
  const qs = rangeParams(search)
  return useQuery(
    queryOptions({
      queryKey: ['journal', qs] as const,
      queryFn: () => apiFetch(`/journal?${qs}`, { schema: listingSchema }),
    }),
  )
}

export function useEntry(entryNo: string) {
  return useQuery(
    queryOptions({
      queryKey: ['journal-entry', entryNo] as const,
      queryFn: () => apiFetch(`/journal/${encodeURIComponent(entryNo)}`, { schema: detailSchema }),
    }),
  )
}

export function usePnl(search: RangeSearch) {
  const qs = rangeParams(search)
  return useQuery(
    queryOptions({
      queryKey: ['pnl', qs] as const,
      queryFn: () => apiFetch(`/reports/pnl?${qs}`, { schema: pnlSchema }),
    }),
  )
}

export function useBalanceSheet(search: RangeSearch) {
  const qs = rangeParams(search)
  return useQuery(
    queryOptions({
      queryKey: ['balance-sheet', qs] as const,
      queryFn: () => apiFetch(`/reports/balance-sheet?${qs}`, { schema: bsSchema }),
    }),
  )
}

export function useTrialBalance(search: RangeSearch) {
  const qs = rangeParams(search)
  return useQuery(
    queryOptions({
      queryKey: ['trial-balance', qs] as const,
      queryFn: () => apiFetch(`/reports/trial-balance?${qs}`, { schema: tbSchema }),
    }),
  )
}

export function documentUrl(documentId: number): string {
  return `/api/documents/${documentId}/file`
}
