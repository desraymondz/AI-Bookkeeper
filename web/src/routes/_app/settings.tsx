import { createFileRoute, Link, Outlet } from '@tanstack/react-router'
import { PageContainer } from '@/components/app-shell/app-shell'
import { PageHeader } from '@/components/page-header'

// See planning/02-design.md#settings
const SETTINGS_SECTIONS = [
  { label: 'Business', to: '/settings/business' },
  { label: 'Chart of accounts', to: '/settings/accounts' },
  { label: 'Opening balances', to: '/settings/opening-balances' },
  { label: 'Fixed assets', to: '/settings/assets' },
  { label: 'Suppliers', to: '/settings/suppliers' },
  { label: 'Users and roles', to: '/settings/users' },
  { label: 'Telegram', to: '/settings/telegram' },
] as const

export const Route = createFileRoute('/_app/settings')({
  component: SettingsLayout,
})

function SettingsLayout() {
  return (
    <PageContainer width="settings">
      <PageHeader title="Settings" />
      <div className="flex flex-col gap-6 lg:flex-row">
        <nav aria-label="Settings" className="overflow-x-auto lg:w-[200px] lg:shrink-0">
          <ul className="flex min-w-max gap-1 lg:min-w-0 lg:flex-col">
            {SETTINGS_SECTIONS.map((section) => (
              <li key={section.to}>
                <Link
                  to={section.to}
                  className="block rounded-md px-3 py-1.5 text-sm whitespace-nowrap hover:text-foreground"
                  activeProps={{
                    'aria-current': 'page',
                    className: 'bg-accent-selected font-semibold text-foreground',
                  }}
                  inactiveProps={{ className: 'text-muted-foreground hover:bg-accent' }}
                >
                  {section.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
        <div className="min-w-0 flex-1 lg:max-w-[560px]">
          <Outlet />
        </div>
      </div>
    </PageContainer>
  )
}
