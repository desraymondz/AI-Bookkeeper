import { useNavigate } from '@tanstack/react-router'
import { PageContainer } from '@/components/app-shell/app-shell'
import { Button } from '@/components/ui/button'
import { logout } from './api'

// See planning/02-design.md#access-denied-f-0011
export function AccessDeniedPage() {
  const navigate = useNavigate()
  const switchAccount = async () => {
    try {
      await logout()
    } finally {
      await navigate({ to: '/sign-in', replace: true })
    }
  }

  return (
    <PageContainer width="narrow">
      <div className="flex flex-col gap-4 pt-16">
        <h1 className="text-xl font-semibold">Access denied</h1>
        <p className="text-muted-foreground">
          This Google account is not allowed. Sign in with the owner's account.
        </p>
        <Button variant="secondary" onClick={switchAccount}>
          Use another account
        </Button>
      </div>
    </PageContainer>
  )
}
