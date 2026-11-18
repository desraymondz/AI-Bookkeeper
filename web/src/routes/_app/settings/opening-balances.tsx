import { createFileRoute } from '@tanstack/react-router'
import { OpeningBalancesPage } from '@/features/opening-balances/opening-balances-page'

// See planning/02-design.md#settings (F-004)
export const Route = createFileRoute('/_app/settings/opening-balances')({
  component: OpeningBalancesPage,
})
