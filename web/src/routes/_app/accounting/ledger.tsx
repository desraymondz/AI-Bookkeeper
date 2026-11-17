import { createFileRoute } from '@tanstack/react-router'
import { PlaceholderSection } from '@/components/placeholder-page'

// See planning/02-design.md#accounting-page (F-025)
export const Route = createFileRoute('/_app/accounting/ledger')({
  component: () => <PlaceholderSection title="General ledger" />,
})
