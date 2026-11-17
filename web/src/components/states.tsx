import { CircleNotchIcon, WarningIcon } from '@phosphor-icons/react'
import type { ReactNode } from 'react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

// See planning/02-design.md#shared-states

export function Spinner({ className }: { className?: string }) {
  return <CircleNotchIcon aria-hidden className={cn('size-4 animate-spin', className)} />
}

function placeholderKeys(prefix: string, count: number) {
  return Array.from({ length: count }, (_, position) => `${prefix}-${position}`)
}

type LoadingStateProps = {
  label?: string
  rows?: number
  className?: string
}

export function LoadingState({ label = 'Loading', rows = 5, className }: LoadingStateProps) {
  return (
    <div role="status" aria-live="polite" className={cn('flex flex-col gap-2', className)}>
      <span className="sr-only">{label}</span>
      {placeholderKeys('row', rows).map((key) => (
        <div key={key} aria-hidden className="h-5 w-full bg-muted" />
      ))}
    </div>
  )
}

export function TableLoadingRows({ columns, rows = 5 }: { columns: number; rows?: number }) {
  return placeholderKeys('row', rows).map((rowKey) => (
    <tr key={rowKey} aria-hidden>
      {placeholderKeys('cell', columns).map((cellKey) => (
        <td key={cellKey} className="px-3 py-1.5">
          <div className="h-4 w-full bg-muted" />
        </td>
      ))}
    </tr>
  ))
}

type EmptyStateProps = {
  message: string
  action?: ReactNode
  className?: string
}

export function EmptyState({ message, action, className }: EmptyStateProps) {
  return (
    <div className={cn('flex max-w-[72ch] flex-col gap-2 py-6 text-base', className)}>
      <p className="text-muted-foreground">{message}</p>
      {action ? <div>{action}</div> : null}
    </div>
  )
}

type ErrorStateProps = {
  message: string
  onRetry?: () => void
  className?: string
}

export function ErrorState({ message, onRetry, className }: ErrorStateProps) {
  return (
    <div role="alert" className={cn('flex flex-wrap items-center gap-3 py-6 text-base', className)}>
      <span className="inline-flex items-center gap-2 text-destructive">
        <WarningIcon aria-hidden className="size-4" />
        {message}
      </span>
      {onRetry ? (
        <Button variant="link" size="sm" onClick={onRetry}>
          Retry
        </Button>
      ) : null}
    </div>
  )
}
