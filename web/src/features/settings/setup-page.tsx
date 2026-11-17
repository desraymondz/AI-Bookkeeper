import { useNavigate } from '@tanstack/react-router'
import { toast } from 'sonner'
import { NAV_ITEMS } from '@/components/app-shell/nav-items'
import { ErrorState, LoadingState } from '@/components/states'
import { useSettings } from './api'
import { SettingsForm } from './settings-form'

// See planning/02-design.md#first-run-setup-f-0021-to-f-0023
export function SetupPage() {
  const navigate = useNavigate()
  const { data, isPending, isError, refetch } = useSettings()

  return (
    <div className="flex min-h-dvh flex-col">
      <header className="sticky top-0 z-40 h-(--header-height) border-b bg-background">
        <div className="mx-auto flex h-full max-w-[1280px] items-center gap-6 px-4 md:px-6">
          <span className="text-base font-semibold">AI Bookkeeper</span>
          <nav aria-label="Main" className="flex gap-5">
            {NAV_ITEMS.map((item) => (
              <span
                key={item.to}
                aria-disabled="true"
                className="cursor-not-allowed text-sm text-muted-foreground opacity-50"
              >
                {item.label}
              </span>
            ))}
          </nav>
        </div>
      </header>
      <main id="main" className="mx-auto flex w-full max-w-[560px] flex-col gap-6 p-4 md:p-6">
        <h1 className="text-xl font-semibold">First-run setup</h1>
        <p className="text-muted-foreground">Set up your business before using the books.</p>
        {isPending ? <LoadingState rows={8} /> : null}
        {isError ? (
          <ErrorState message="Could not load the setup form." onRetry={() => void refetch()} />
        ) : null}
        {data ? (
          <SettingsForm
            initial={data.settings ?? data.defaults}
            submitLabel="Save and continue"
            onSaved={async () => {
              await navigate({ to: '/settings/telegram' })
              toast.success('Settings saved')
            }}
          />
        ) : null}
      </main>
    </div>
  )
}
