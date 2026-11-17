import { createFileRoute } from '@tanstack/react-router'
import { PlaceholderSection } from '@/components/placeholder-page'

// See planning/02-design.md#accounting-page (F-026.2)
export const Route = createFileRoute('/_app/accounting/adjusted-trial-balance')({
  component: () => <PlaceholderSection title="Adjusted trial balance" />,
})
