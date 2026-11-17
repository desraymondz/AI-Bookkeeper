import { useQueryClient } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import type { ReactNode } from 'react'
import { AppHeader } from './app-header'

export function AppShell({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  // TODO(P1-T07): call the sign-out endpoint from P1-T04 before clearing. See planning/01-prd.md#F-001
  const signOut = () => {
    queryClient.clear()
    void navigate({ to: '/sign-in' })
  }

  return (
    <div className="flex min-h-dvh flex-col">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 focus:rounded-md focus:bg-background focus:px-3 focus:py-2 focus:text-sm"
      >
        Skip to content
      </a>
      <AppHeader onSignOut={signOut} />
      <main id="main" tabIndex={-1} className="flex-1">
        {children}
      </main>
    </div>
  )
}

export function PageContainer({
  children,
  width = 'wide',
}: {
  children: ReactNode
  width?: 'wide' | 'settings' | 'narrow'
}) {
  const maxWidth = { wide: 'max-w-[1280px]', settings: 'max-w-[960px]', narrow: 'max-w-[440px]' }[
    width
  ]
  return (
    <div className={`mx-auto flex w-full ${maxWidth} flex-col gap-6 p-4 md:p-6`}>{children}</div>
  )
}
