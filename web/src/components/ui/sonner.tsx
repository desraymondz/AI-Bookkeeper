import { CheckIcon, WarningIcon } from '@phosphor-icons/react'
import type { CSSProperties } from 'react'
import { Toaster as Sonner } from 'sonner'
import { useIsDesktop } from '@/lib/use-media-query'

// See planning/02-design.md#global-components (Toast)
export function Toaster() {
  const isDesktop = useIsDesktop()
  return (
    <Sonner
      position={isDesktop ? 'bottom-right' : 'bottom-center'}
      duration={4000}
      visibleToasts={3}
      icons={{
        success: <CheckIcon aria-hidden className="size-4" />,
        error: <WarningIcon aria-hidden className="size-4" />,
      }}
      toastOptions={{
        classNames: {
          toast: 'text-sm',
          error: 'text-destructive',
        },
      }}
      style={
        {
          '--normal-bg': 'var(--popover)',
          '--normal-text': 'var(--popover-foreground)',
          '--normal-border': 'var(--border)',
          '--border-radius': 'var(--radius)',
          '--font-family': 'inherit',
        } as CSSProperties
      }
    />
  )
}
