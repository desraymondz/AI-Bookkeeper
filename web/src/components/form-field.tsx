import type { ReactNode } from 'react'
import { Label } from '@/components/ui/label'

type FormFieldProps = {
  id: string
  label: string
  error?: string
  hint?: string
  children: (props: {
    id: string
    'aria-invalid': boolean
    'aria-describedby': string | undefined
  }) => ReactNode
}

// See planning/02-design.md#shared-states (Error)
export function FormField({ id, label, error, hint, children }: FormFieldProps) {
  const errorId = `${id}-error`
  const hintId = `${id}-hint`
  const describedBy = [error ? errorId : null, hint ? hintId : null].filter(Boolean).join(' ')
  return (
    <div className="flex flex-col gap-1.5">
      <Label htmlFor={id}>{label}</Label>
      {children({
        id,
        'aria-invalid': Boolean(error),
        'aria-describedby': describedBy || undefined,
      })}
      {hint ? (
        <p id={hintId} className="text-xs text-muted-foreground">
          {hint}
        </p>
      ) : null}
      <p id={errorId} aria-live="polite" className="text-xs text-destructive empty:hidden">
        {error}
      </p>
    </div>
  )
}
