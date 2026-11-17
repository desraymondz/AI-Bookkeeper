import { createFileRoute } from '@tanstack/react-router'
import { PlaceholderSection } from '@/components/placeholder-page'

// See planning/02-design.md#accounting-page (F-027.3)
export const Route = createFileRoute('/_app/accounting/cash-flow')({
  component: () => <PlaceholderSection title="Cash flow" />,
})
