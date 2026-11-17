import { createFileRoute } from '@tanstack/react-router'
import { PlaceholderSection } from '@/components/placeholder-page'

// See planning/02-design.md#accounting-page (F-024)
export const Route = createFileRoute('/_app/accounting/journal')({
  component: () => <PlaceholderSection title="Journal" />,
})
