import { cva, type VariantProps } from 'class-variance-authority'
import type * as React from 'react'
import { cn } from '@/lib/utils'

// See planning/02-design.md#global-components
const badgeVariants = cva(
  'inline-flex h-5 items-center rounded-md px-1.5 text-xs font-medium whitespace-nowrap',
  {
    variants: {
      variant: {
        outline: 'border border-foreground bg-transparent text-foreground',
        filled: 'bg-foreground text-background',
        muted: 'bg-muted text-muted-foreground',
      },
    },
    defaultVariants: { variant: 'outline' },
  },
)

function Badge({
  className,
  variant,
  ...props
}: React.ComponentProps<'span'> & VariantProps<typeof badgeVariants>) {
  return <span data-slot="badge" className={cn(badgeVariants({ variant }), className)} {...props} />
}

export { Badge }
