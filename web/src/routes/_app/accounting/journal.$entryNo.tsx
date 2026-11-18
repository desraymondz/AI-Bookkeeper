import { createFileRoute } from '@tanstack/react-router'
import { EntrySheet } from '@/features/books/entry-sheet'

// See planning/02-design.md#entry-detail-sheet-f-0243
export const Route = createFileRoute('/_app/accounting/journal/$entryNo')({
  component: EntryRoute,
})

function EntryRoute() {
  const { entryNo } = Route.useParams()
  return <EntrySheet entryNo={entryNo} />
}
