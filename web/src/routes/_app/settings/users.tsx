import { createFileRoute } from '@tanstack/react-router'
import { UsersPage } from '@/features/users/users-page'

// See planning/02-design.md#settings (F-008)
export const Route = createFileRoute('/_app/settings/users')({
  component: UsersPage,
})
