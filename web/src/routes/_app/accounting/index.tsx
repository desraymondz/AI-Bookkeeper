import { createFileRoute, redirect } from '@tanstack/react-router'

export const Route = createFileRoute('/_app/accounting/')({
  beforeLoad: ({ search }) => {
    throw redirect({ to: '/accounting/journal', search })
  },
})
