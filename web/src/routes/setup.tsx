import { createFileRoute, redirect } from '@tanstack/react-router'
import { requireSession } from '@/features/auth/api'
import { settingsQuery } from '@/features/settings/api'
import { SetupPage } from '@/features/settings/setup-page'

// See planning/02-design.md#12-screens (F-002.1)
export const Route = createFileRoute('/setup')({
  beforeLoad: async ({ context }) => {
    await requireSession(context.queryClient)
    const state = await context.queryClient.fetchQuery(settingsQuery)
    if (state.configured) throw redirect({ to: '/settings/business' })
  },
  component: SetupPage,
})
