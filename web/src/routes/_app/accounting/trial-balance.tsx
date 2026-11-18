import { createFileRoute } from '@tanstack/react-router'
import { TrialBalancePage } from '@/features/books/statements'

// See planning/02-design.md#accounting-page (F-026.1)
export const Route = createFileRoute('/_app/accounting/trial-balance')({
  component: TrialBalancePage,
})
