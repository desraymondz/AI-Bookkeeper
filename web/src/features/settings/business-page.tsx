import { toast } from 'sonner'
import { ErrorState, LoadingState } from '@/components/states'
import { useSettings } from './api'
import { SettingsForm } from './settings-form'

// See planning/02-design.md#settings
export function BusinessPage() {
  const { data, isPending, isError, refetch } = useSettings()

  return (
    <section className="flex flex-col gap-4">
      <h2 className="text-lg font-semibold">Business</h2>
      {isPending ? <LoadingState rows={8} /> : null}
      {isError ? (
        <ErrorState message="Could not load settings." onRetry={() => void refetch()} />
      ) : null}
      {data ? (
        <SettingsForm
          key={JSON.stringify(data.settings)}
          initial={data.settings ?? data.defaults}
          submitLabel="Save"
          onSaved={() => {
            toast.success('Settings saved')
          }}
          footer={
            <p className="text-sm text-muted-foreground">Changes apply to new events only.</p>
          }
        />
      ) : null}
    </section>
  )
}
