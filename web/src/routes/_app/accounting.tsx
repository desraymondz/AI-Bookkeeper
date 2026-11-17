import { createFileRoute, Link, Outlet } from '@tanstack/react-router'
import { zodValidator } from '@tanstack/zod-adapter'
import { PageContainer } from '@/components/app-shell/app-shell'
import { PageHeader } from '@/components/page-header'
import { rangeSearchSchema } from '@/lib/search'

// See planning/02-design.md#accounting-page
const ACCOUNTING_TABS = [
  { label: 'Journal', to: '/accounting/journal' },
  { label: 'General ledger', to: '/accounting/ledger' },
  { label: 'Trial balance', to: '/accounting/trial-balance' },
  { label: 'Adjusted trial balance', to: '/accounting/adjusted-trial-balance' },
  { label: 'P&L', to: '/accounting/pnl' },
  { label: 'Balance sheet', to: '/accounting/balance-sheet' },
  { label: 'Cash flow', to: '/accounting/cash-flow' },
] as const

export const Route = createFileRoute('/_app/accounting')({
  validateSearch: zodValidator(rangeSearchSchema),
  component: AccountingLayout,
})

function AccountingLayout() {
  return (
    <PageContainer>
      <PageHeader title="Accounting" />
      <nav aria-label="Accounting" className="-mt-2 overflow-x-auto border-b">
        <ul className="flex min-w-max gap-5">
          {ACCOUNTING_TABS.map((tab) => (
            <li key={tab.to}>
              <Link
                to={tab.to}
                search={(prev) => prev}
                className="-mb-px inline-flex h-9 items-center border-b-2 text-sm whitespace-nowrap hover:text-foreground"
                activeProps={{
                  'aria-current': 'page',
                  className: 'border-primary font-semibold text-foreground',
                }}
                inactiveProps={{ className: 'border-transparent text-muted-foreground' }}
              >
                {tab.label}
              </Link>
            </li>
          ))}
        </ul>
      </nav>
      <Outlet />
    </PageContainer>
  )
}
