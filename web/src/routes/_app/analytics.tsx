import { createFileRoute } from '@tanstack/react-router'
import { zodValidator } from '@tanstack/zod-adapter'
import { PageContainer } from '@/components/app-shell/app-shell'
import { PageHeader } from '@/components/page-header'
import { EmptyState } from '@/components/states'
import { rangeSearchSchema } from '@/lib/search'

// See planning/02-design.md#analytics-f-028
export const Route = createFileRoute('/_app/analytics')({
  validateSearch: zodValidator(rangeSearchSchema),
  component: AnalyticsPage,
})

function AnalyticsPage() {
  return (
    <PageContainer>
      <PageHeader title="Analytics" />
      <EmptyState message="Not built yet." />
    </PageContainer>
  )
}
