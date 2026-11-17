import { QueryClient } from '@tanstack/react-query'
import { ApiError } from './api'

type QueryClientOptions = {
  retry?: boolean
}

export function createQueryClient({ retry = true }: QueryClientOptions = {}) {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        refetchOnWindowFocus: false,
        retry: retry
          ? (failureCount, error) =>
              !(error instanceof ApiError && error.status < 500) && failureCount < 2
          : false,
      },
      mutations: {
        retry: false,
      },
    },
  })
}

export const queryKeys = {
  config: ['config'] as const,
}
