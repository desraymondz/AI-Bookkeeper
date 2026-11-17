import { createFileRoute } from '@tanstack/react-router'
import { PageContainer } from '@/components/app-shell/app-shell'
import { EmptyState } from '@/components/states'

// See planning/02-design.md#12-screens (F-001.1)
export const Route = createFileRoute('/sign-in')({
  component: Page,
})

function Page() {
  return (
    <PageContainer width="narrow">
      <h1 className="text-xl font-semibold">Sign in</h1>
      <EmptyState message="Not built yet." />
    </PageContainer>
  )
}
