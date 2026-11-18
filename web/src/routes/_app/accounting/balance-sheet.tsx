import { createFileRoute } from '@tanstack/react-router'
import { BalanceSheetPage } from '@/features/books/statements'

// See planning/02-design.md#accounting-page (F-027.2)
export const Route = createFileRoute('/_app/accounting/balance-sheet')({
  component: BalanceSheetPage,
})
