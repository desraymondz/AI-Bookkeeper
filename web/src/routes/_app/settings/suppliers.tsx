import { createFileRoute } from '@tanstack/react-router'
import { SuppliersPage } from '@/features/suppliers/suppliers-page'

// See planning/02-design.md#settings (F-007)
export const Route = createFileRoute('/_app/settings/suppliers')({
  component: SuppliersPage,
})
