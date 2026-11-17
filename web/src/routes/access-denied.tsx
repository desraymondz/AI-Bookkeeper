import { createFileRoute } from '@tanstack/react-router'
import { PageContainer } from '@/components/app-shell/app-shell'
import { EmptyState } from '@/components/states'

// See planning/02-design.md#12-screens (F-001.1)
export const Route = createFileRoute('/access-denied')({
  component: Page,
})

function Page() {
  return (
    <PageContainer width="narrow">
      <h1 className="text-xl font-semibold">Access denied</h1>
      <EmptyState message="Not built yet." />
    </PageContainer>
  )
}
