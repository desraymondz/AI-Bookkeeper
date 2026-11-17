import { Link, useLocation } from '@tanstack/react-router'
import { useAppConfig } from '@/features/config/api'
import { useIsDesktop } from '@/lib/use-media-query'
import { cn } from '@/lib/utils'
import { AccountMenu } from './account-menu'
import { MobileNav } from './mobile-nav'
import { isSectionActive, NAV_ITEMS } from './nav-items'
import { OpenTelegramButton } from './open-telegram-button'
import { ThemeToggle } from './theme-toggle'

export const DEFAULT_BUSINESS_NAME = 'AI Bookkeeper'

type AppHeaderProps = {
  email?: string | null
  onSignOut: () => void
}

// See planning/02-design.md#app-shell and #responsive
export function AppHeader({ email, onSignOut }: AppHeaderProps) {
  const isDesktop = useIsDesktop()
  const { data: config } = useAppConfig()
  const pathname = useLocation({ select: (location) => location.pathname })
  const businessName = config?.business_name || DEFAULT_BUSINESS_NAME

  return (
    <header className="sticky top-0 z-40 h-(--header-height) border-b bg-background">
      <div className="mx-auto flex h-full max-w-[1280px] items-center gap-2 px-4 md:gap-6 md:px-6">
        {isDesktop ? null : <MobileNav businessName={businessName} onSignOut={onSignOut} />}
        <Link
          to="/accounting/journal"
          search={{ range: 'this-month' }}
          className="min-w-0 truncate text-base font-semibold"
        >
          {businessName}
        </Link>
        {isDesktop ? (
          <>
            <nav aria-label="Main" className="flex h-full items-stretch gap-5">
              {NAV_ITEMS.map((item) => {
                const active = isSectionActive(pathname, item.section)
                return (
                  <Link
                    key={item.to}
                    to={item.to}
                    aria-current={active ? 'page' : undefined}
                    className={cn(
                      'inline-flex items-center border-b-2 border-transparent pt-0.5 text-sm text-muted-foreground hover:text-foreground',
                      active && 'border-primary font-semibold text-foreground',
                    )}
                  >
                    {item.label}
                  </Link>
                )
              })}
            </nav>
            <div className="ml-auto flex items-center gap-1">
              <OpenTelegramButton className="mr-1" />
              <ThemeToggle />
              <AccountMenu email={email} onSignOut={onSignOut} />
            </div>
          </>
        ) : null}
      </div>
    </header>
  )
}
