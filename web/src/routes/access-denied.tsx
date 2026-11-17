import { createFileRoute } from '@tanstack/react-router'
import { AccessDeniedPage } from '@/features/auth/access-denied-page'

// See planning/02-design.md#12-screens (F-001.1)
export const Route = createFileRoute('/access-denied')({
  component: AccessDeniedPage,
})
