import { createFileRoute } from '@tanstack/react-router'
import { PlaceholderSection } from '@/components/placeholder-page'

// See planning/02-design.md#accounting-page (F-027.1)
export const Route = createFileRoute('/_app/accounting/pnl')({
  component: () => <PlaceholderSection title="P&L" />,
})
