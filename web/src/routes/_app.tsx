import { createFileRoute, Outlet, redirect } from '@tanstack/react-router'
import { AppShell } from '@/components/app-shell/app-shell'
import { requireSession } from '@/features/auth/api'
import { settingsQuery } from '@/features/settings/api'

// See planning/01-prd.md#F-001 (F-001.2) and #F-002 (F-002.1)
export const Route = createFileRoute('/_app')({
  beforeLoad: async ({ context }) => {
    await requireSession(context.queryClient)
    const state = await context.queryClient.fetchQuery(settingsQuery)
    if (!state.configured) throw redirect({ to: '/setup' })
  },
  component: AppLayout,
})

function AppLayout() {
  return (
    <AppShell>
      <Outlet />
    </AppShell>
  )
}
