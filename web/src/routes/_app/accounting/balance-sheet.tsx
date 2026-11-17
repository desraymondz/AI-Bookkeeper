import { createFileRoute } from '@tanstack/react-router'
import { PlaceholderSection } from '@/components/placeholder-page'

// See planning/02-design.md#accounting-page (F-027.2)
export const Route = createFileRoute('/_app/accounting/balance-sheet')({
  component: () => <PlaceholderSection title="Balance sheet" />,
})
