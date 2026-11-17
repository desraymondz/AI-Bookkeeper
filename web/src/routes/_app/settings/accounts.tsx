import { createFileRoute } from '@tanstack/react-router'
import { AccountsPage } from '@/features/accounts/accounts-page'

// See planning/02-design.md#settings (F-003)
export const Route = createFileRoute('/_app/settings/accounts')({
  component: AccountsPage,
})
