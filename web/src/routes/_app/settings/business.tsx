import { createFileRoute } from '@tanstack/react-router'
import { BusinessPage } from '@/features/settings/business-page'

// See planning/02-design.md#settings (F-002)
export const Route = createFileRoute('/_app/settings/business')({
  component: BusinessPage,
})
