import { CaretDownIcon } from '@phosphor-icons/react'
import type * as React from 'react'
import { cn } from '@/lib/utils'

// See planning/02-design.md#global-components
function Select({ className, children, ...props }: React.ComponentProps<'select'>) {
  return (
    <div className="relative w-full">
      <select
        data-slot="select"
        className={cn(
          'h-8 w-full appearance-none rounded-md border border-input bg-transparent pr-8 pl-3 text-sm outline-none hover:border-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring disabled:cursor-not-allowed disabled:opacity-50 aria-invalid:border-destructive',
          className,
        )}
        {...props}
      >
        {children}
      </select>
      <CaretDownIcon
        aria-hidden
        className="pointer-events-none absolute top-1/2 right-2.5 size-4 -translate-y-1/2 text-muted-foreground"
      />
    </div>
  )
}

export { Select }
