import { createFileRoute } from '@tanstack/react-router'
import { PnlPage } from '@/features/books/statements'

// See planning/02-design.md#accounting-page (F-027.1)
export const Route = createFileRoute('/_app/accounting/pnl')({
  component: PnlPage,
})
