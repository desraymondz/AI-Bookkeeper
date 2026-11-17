import { createFileRoute } from '@tanstack/react-router'
import { PlaceholderSection } from '@/components/placeholder-page'

// See planning/02-design.md#settings (F-007)
export const Route = createFileRoute('/_app/settings/suppliers')({
  component: () => <PlaceholderSection title="Suppliers" />,
})
