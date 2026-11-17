import { useQueryClient } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { useCallback } from 'react'
import { logout } from './api'

// See planning/01-prd.md#F-001 (F-001.3)
export function useSignOut() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  return useCallback(async () => {
    try {
      await logout()
    } finally {
      queryClient.clear()
      await navigate({ to: '/sign-in' })
    }
  }, [queryClient, navigate])
}
