import { useState } from 'react'
import { PageContainer } from '@/components/app-shell/app-shell'
import { Spinner } from '@/components/states'
import { Button } from '@/components/ui/button'
import { useAppConfig } from '@/features/config/api'
import { GOOGLE_LOGIN_URL } from './api'

const DEFAULT_NAME = 'AI Bookkeeper'

// See planning/02-design.md#sign-in-f-0011
export function SignInPage({ failed }: { failed: boolean }) {
  const { data: config } = useAppConfig()
  const [redirecting, setRedirecting] = useState(false)

  return (
    <PageContainer width="narrow">
      <div className="flex flex-col gap-4 pt-16">
        <h1 className="text-xl font-semibold">{config?.business_name || DEFAULT_NAME}</h1>
        <p className="text-muted-foreground">Sign in to view the books.</p>
        {failed ? (
          <p role="alert" className="text-sm text-destructive">
            Sign-in failed. Try again.
          </p>
        ) : null}
        <Button asChild>
          <a
            href={GOOGLE_LOGIN_URL}
            aria-disabled={redirecting}
            onClick={() => setRedirecting(true)}
          >
            {redirecting ? <Spinner /> : null}
            Continue with Google
          </a>
        </Button>
      </div>
    </PageContainer>
  )
}
