import { CalendarBlankIcon } from '@phosphor-icons/react'
import { useNavigate, useSearch } from '@tanstack/react-router'
import { Select } from '@/components/ui/select'
import { formatDate, formatRange } from '@/lib/format'
import type { RangePreset, RangeSearch } from '@/lib/search'

// See planning/02-design.md#date-range-filter-f-0242-f-0252-f-0284

export const PRESET_LABELS: Record<Exclude<RangePreset, 'custom'>, string> = {
  'this-month': 'This month',
  'last-month': 'Last month',
  'last-3-months': 'Last 3 months',
  'year-to-date': 'Year to date',
  'last-12-months': 'Last 12 months',
}

export function useRange(): RangeSearch {
  return useSearch({ from: '/_app/accounting' })
}

type RangeFilterProps = {
  start?: string
  end?: string
  asAt?: boolean
}

export function RangeFilter({ start, end, asAt = false }: RangeFilterProps) {
  const search = useRange()
  const navigate = useNavigate()
  const preset: Exclude<RangePreset, 'custom'> =
    search.range === 'custom' ? 'this-month' : search.range
  const span = start && end ? (asAt ? `As at ${formatDate(end)}` : formatRange(start, end)) : ''
  return (
    <div className="flex flex-wrap items-center gap-3">
      <div className="inline-flex items-center gap-2 text-sm">
        <CalendarBlankIcon aria-hidden className="size-4" />
        <Select
          aria-label="Date range"
          value={preset}
          onChange={(event) =>
            void navigate({
              to: '.',
              search: (prev: RangeSearch) => ({
                ...prev,
                range: event.target.value as RangePreset,
                from: undefined,
                to: undefined,
              }),
            })
          }
        >
          {Object.entries(PRESET_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </Select>
      </div>
      <span data-testid="range-label" className="text-sm text-muted-foreground">
        {PRESET_LABELS[preset]}
        {span ? `: ${span}` : ''}
      </span>
    </div>
  )
}
