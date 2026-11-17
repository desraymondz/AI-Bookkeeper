import { createFileRoute } from '@tanstack/react-router'
import { PlaceholderSection } from '@/components/placeholder-page'

// See planning/02-design.md#settings (F-003)
export const Route = createFileRoute('/_app/settings/accounts')({
  component: () => <PlaceholderSection title="Chart of accounts" />,
})
