import { createFileRoute, redirect } from '@tanstack/react-router'
import { z } from 'zod'
import { readSession } from '@/features/auth/api'
import { SignInPage } from '@/features/auth/sign-in-page'

// See planning/02-design.md#12-screens (F-001.1)
export const Route = createFileRoute('/sign-in')({
  validateSearch: z.object({ error: z.string().optional().catch(undefined) }),
  beforeLoad: async ({ context }) => {
    if (await readSession(context.queryClient)) {
      throw redirect({ to: '/accounting/journal', search: { range: 'this-month' } })
    }
  },
  component: Page,
})

function Page() {
  const { error } = Route.useSearch()
  return <SignInPage failed={Boolean(error)} />
}
