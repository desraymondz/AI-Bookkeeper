import { WarningIcon } from '@phosphor-icons/react'
import { formatMoney, isZero } from '@/lib/format'

// See planning/02-design.md#accounting-page (TB imbalance warning) and AGENTS.md (report numbers)

type TotalsMismatchProps = {
  debit: string
  credit: string
  difference?: string
}

export function TotalsMismatch({ debit, credit, difference }: TotalsMismatchProps) {
  const mismatch = difference !== undefined ? !isZero(difference) : debit !== credit
  if (!mismatch) return null
  const text =
    difference !== undefined
      ? `Totals do not match. Difference: S$${formatMoney(difference, { parens: false })}.`
      : `Totals do not match. Total debit ${formatMoney(debit)}, total credit ${formatMoney(credit)}.`
  return (
    <div
      role="alert"
      className="flex items-center gap-2 border border-destructive px-3 py-2 text-sm"
    >
      <WarningIcon aria-hidden className="size-4" />
      {text}
    </div>
  )
}
