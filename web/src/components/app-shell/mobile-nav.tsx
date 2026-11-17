import { ListIcon } from '@phosphor-icons/react'
import { Link, useLocation } from '@tanstack/react-router'
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet'
import { cn } from '@/lib/utils'
import { isSectionActive, NAV_ITEMS } from './nav-items'
import { OpenTelegramButton } from './open-telegram-button'
import { ThemeToggle } from './theme-toggle'

type MobileNavProps = {
  businessName: string
  onSignOut: () => void
}

export function MobileNav({ businessName, onSignOut }: MobileNavProps) {
  const [open, setOpen] = useState(false)
  const pathname = useLocation({ select: (location) => location.pathname })

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <Button variant="ghost" size="icon" aria-label="Open menu">
          <ListIcon aria-hidden />
        </Button>
      </SheetTrigger>
      <SheetContent side="left" className="gap-0">
        <SheetHeader className="border-b">
          <SheetTitle className="truncate pr-8">{businessName}</SheetTitle>
          <SheetDescription className="sr-only">Site navigation</SheetDescription>
        </SheetHeader>
        <nav aria-label="Main" className="flex flex-col p-2">
          {NAV_ITEMS.map((item) => {
            const active = isSectionActive(pathname, item.section)
            return (
              <Link
                key={item.to}
                to={item.to}
                aria-current={active ? 'page' : undefined}
                onClick={() => setOpen(false)}
                className={cn(
                  'rounded-md px-3 py-2 text-base hover:bg-accent',
                  active && 'font-semibold underline decoration-2 underline-offset-4',
                )}
              >
                {item.label}
              </Link>
            )
          })}
        </nav>
        <div className="flex flex-col gap-2 border-t p-4">
          <OpenTelegramButton className="justify-start" />
          <ThemeToggle withLabel />
          <Button
            variant="ghost"
            className="justify-start"
            onClick={() => {
              setOpen(false)
              onSignOut()
            }}
          >
            Sign out
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  )
}
