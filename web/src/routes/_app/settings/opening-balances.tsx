import { createFileRoute } from '@tanstack/react-router'
import { PlaceholderSection } from '@/components/placeholder-page'

// See planning/02-design.md#settings (F-004)
export const Route = createFileRoute('/_app/settings/opening-balances')({
  component: () => <PlaceholderSection title="Opening balances" />,
})
