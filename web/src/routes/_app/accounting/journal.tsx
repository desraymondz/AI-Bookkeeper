import { createFileRoute, Outlet } from '@tanstack/react-router'
import { JournalPage } from '@/features/books/journal-page'

// See planning/02-design.md#accounting-page (F-024)
export const Route = createFileRoute('/_app/accounting/journal')({
  component: () => (
    <>
      <JournalPage />
      <Outlet />
    </>
  ),
})
