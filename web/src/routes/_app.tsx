import { createFileRoute, Outlet } from '@tanstack/react-router'
import { AppShell } from '@/components/app-shell/app-shell'

// TODO(P1-T07): add the session guard (F-001.2) and setup redirect (F-002.1) in beforeLoad.
export const Route = createFileRoute('/_app')({
  component: AppLayout,
})

function AppLayout() {
  return (
    <AppShell>
      <Outlet />
    </AppShell>
  )
}
