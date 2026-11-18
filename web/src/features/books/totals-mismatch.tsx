import { WarningIcon } from '@phosphor-icons/react'

// See planning/02-design.md#accounting-page (TB imbalance warning)

function cents(value: string): bigint {
  const negative = value.trim().startsWith('-')
  const [whole = '0', fraction = ''] = value.trim().replace(/^[-+]/, '').split('.')
  const amount = BigInt(whole || '0') * 100n + BigInt(`${fraction}00`.slice(0, 2))
  return negative ? -amount : amount
}

export function TotalsMismatch({ debit, credit }: { debit: string; credit: string }) {
  const diff = cents(debit) - cents(credit)
  if (diff === 0n) return null
  const abs = diff < 0n ? -diff : diff
  const text = `${abs / 100n}.${(abs % 100n).toString().padStart(2, '0')}`
  return (
    <div
      role="alert"
      className="flex items-center gap-2 border border-destructive px-3 py-2 text-sm"
    >
      <WarningIcon aria-hidden className="size-4" />
      Totals do not match. Difference: S${text}.
    </div>
  )
}
