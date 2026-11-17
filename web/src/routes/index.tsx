import { createFileRoute, redirect } from '@tanstack/react-router'

// See planning/02-design.md#8-screen-inventory
export const Route = createFileRoute('/')({
  beforeLoad: () => {
    throw redirect({ to: '/accounting/journal', search: { range: 'this-month' } })
  },
})
