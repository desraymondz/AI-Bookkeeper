import { createFileRoute } from '@tanstack/react-router'
import { PlaceholderSection } from '@/components/placeholder-page'

// See planning/02-design.md#settings (F-021)
export const Route = createFileRoute('/_app/settings/assets')({
  component: () => <PlaceholderSection title="Fixed assets" />,
})
