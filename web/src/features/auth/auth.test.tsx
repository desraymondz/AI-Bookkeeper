import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { HttpResponse, http } from 'msw'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { renderApp } from '@/test/render'
import { server } from '@/test/server'
import { setViewportWidth } from '@/test/viewport'

const signedOut = http.get('*/api/auth/me', () =>
  HttpResponse.json({ detail: 'Not signed in' }, { status: 401 }),
)

describe('T-027 auth guard', () => {
  it.each(['/accounting/journal?range=this-month', '/analytics', '/settings/business'])(
    'redirects %s to /sign-in without a session',
    async (path) => {
      server.use(signedOut)
      const { router } = renderApp(path)
      await screen.findByRole('link', { name: 'Continue with Google' })
      expect(router.state.location.pathname).toBe('/sign-in')
    },
  )
})

describe('T-023 sign-in', () => {
  it('sends a signed-in boss from /sign-in to the journal', async () => {
    const { router } = renderApp('/sign-in')
    await waitFor(() => expect(router.state.location.pathname).toBe('/accounting/journal'))
    expect(router.state.location.search).toMatchObject({ range: 'this-month' })
  })

  it('links Continue with Google to the API login route', async () => {
    server.use(signedOut)
    renderApp('/sign-in')
    const link = await screen.findByRole('link', { name: 'Continue with Google' })
    expect(link).toHaveAttribute('href', '/api/auth/login')
  })
})

describe('T-024 access denied', () => {
  it('shows Access denied without calling /api/config', async () => {
    const config = vi.fn()
    server.use(
      http.get('*/api/config', () => {
        config()
        return HttpResponse.json({ bot_username: null, business_name: 'Kopi Corner' })
      }),
    )
    renderApp('/access-denied')
    await screen.findByRole('heading', { name: 'Access denied' })
    expect(screen.queryByText('Kopi Corner')).not.toBeInTheDocument()
    expect(config).not.toHaveBeenCalled()
  })
})

describe('T-028 sign out', () => {
  it('calls logout, clears the cache and lands on /sign-in', async () => {
    const logout = vi.fn()
    server.use(
      http.post('*/api/auth/logout', () => {
        logout()
        return new HttpResponse(null, { status: 204 })
      }),
    )
    const user = userEvent.setup()
    const { router, queryClient } = renderApp('/accounting/journal?range=this-month')
    await user.click(await screen.findByRole('button', { name: 'Account' }))
    server.use(signedOut)
    await user.click(await screen.findByRole('menuitem', { name: 'Sign out' }))
    await waitFor(() => expect(router.state.location.pathname).toBe('/sign-in'))
    expect(logout).toHaveBeenCalledTimes(1)
    expect(queryClient.getQueryData(['settings'])).toBeUndefined()
  })
})

beforeEach(() => {
  setViewportWidth(1280)
})
