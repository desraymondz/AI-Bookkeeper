import type { QueryClient } from '@tanstack/react-query'
import { createRootRouteWithContext, Link, Outlet } from '@tanstack/react-router'
import { PageContainer } from '@/components/app-shell/app-shell'
import { ErrorState } from '@/components/states'

export type RouterContext = {
  queryClient: QueryClient
}

export const Route = createRootRouteWithContext<RouterContext>()({
  component: Outlet,
  notFoundComponent: NotFound,
  errorComponent: ({ reset }) => (
    <PageContainer width="narrow">
      <ErrorState message="Something went wrong loading this page." onRetry={reset} />
    </PageContainer>
  ),
})

function NotFound() {
  return (
    <PageContainer width="narrow">
      <h1 className="text-xl font-semibold">Page not found</h1>
      <p className="text-muted-foreground">
        This page does not exist.{' '}
        <Link
          to="/accounting/journal"
          search={{ range: 'this-month' }}
          className="underline text-foreground hover:decoration-2"
        >
          Go to the journal
        </Link>
      </p>
    </PageContainer>
  )
}
