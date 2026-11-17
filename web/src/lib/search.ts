import { fallback } from '@tanstack/zod-adapter'
import { z } from 'zod'

// See planning/02-design.md#7-routes-spa and #date-range-filter
export const RANGE_PRESETS = [
  'this-month',
  'last-month',
  'last-3-months',
  'year-to-date',
  'last-12-months',
  'custom',
] as const

export type RangePreset = (typeof RANGE_PRESETS)[number]

export const rangeSearchSchema = z.object({
  range: fallback(z.enum(RANGE_PRESETS), 'this-month').default('this-month'),
  from: z.iso.date().optional().catch(undefined),
  to: z.iso.date().optional().catch(undefined),
})

export type RangeSearch = z.infer<typeof rangeSearchSchema>
