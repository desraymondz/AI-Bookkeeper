import { QueryClientProvider } from '@tanstack/react-query'
import { createMemoryHistory, createRouter, RouterProvider } from '@tanstack/react-router'
import { render } from '@testing-library/react'
import { TooltipProvider } from '@/components/ui/tooltip'
import { createQueryClient } from '@/lib/query'
import { routeTree } from '@/routeTree.gen'

export function renderApp(path: string) {
  const queryClient = createQueryClient({ retry: false })
  const router = createRouter({
    routeTree,
    context: { queryClient },
    history: createMemoryHistory({ initialEntries: [path] }),
  })
  const view = render(
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <RouterProvider router={router} />
      </TooltipProvider>
    </QueryClientProvider>,
  )
  return { ...view, router, queryClient }
}
