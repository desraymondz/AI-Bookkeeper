import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { HttpResponse, http } from 'msw'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { renderApp } from '@/test/render'
import { server, TEST_DEFAULTS } from '@/test/server'
import { setViewportWidth } from '@/test/viewport'

const unconfigured = http.get('*/api/settings', () =>
  HttpResponse.json({ configured: false, settings: null, defaults: TEST_DEFAULTS }),
)

describe('T-030 first-run redirect', () => {
  it('sends an unconfigured boss to /setup with disabled nav', async () => {
    server.use(unconfigured)
    const { router } = renderApp('/analytics')
    await screen.findByRole('heading', { name: 'First-run setup' })
    expect(router.state.location.pathname).toBe('/setup')
    expect(screen.queryByRole('link', { name: 'Analytics' })).not.toBeInTheDocument()
    expect(screen.getByText('Analytics')).toHaveAttribute('aria-disabled', 'true')
  })
})

describe('T-031 setup defaults', () => {
  it('pre-fills the defaults', async () => {
    server.use(unconfigured)
    renderApp('/setup')
    expect(await screen.findByLabelText('Currency')).toHaveValue('SGD')
    expect(screen.getByLabelText('Timezone')).toHaveValue('Asia/Singapore')
    expect(screen.getByLabelText('GST rate (%)')).toHaveValue('9')
    expect(screen.getByLabelText('Price-change rule')).toHaveDisplayValue('Any unit price change')
    expect(screen.getByLabelText('Duplicate window (days)')).toHaveValue('180')
    expect(screen.getByLabelText('Bill reminder lead (days)')).toHaveValue('3')
    expect(screen.getByLabelText('Daily recap time')).toHaveValue('21:00')
    expect(screen.getByLabelText('Monthly report day')).toHaveValue('1')
    expect(screen.getByLabelText('Monthly report time')).toHaveValue('09:00')
  })
})

describe('T-032 setup save', () => {
  it('saves and goes to /settings/telegram', async () => {
    server.use(unconfigured)
    const put = vi.fn()
    server.use(
      http.put('*/api/settings', async ({ request }) => {
        const body = (await request.json()) as Record<string, unknown>
        put(body)
        return HttpResponse.json(body)
      }),
    )
    const user = userEvent.setup()
    const { router } = renderApp('/setup')
    await user.type(await screen.findByLabelText('Business name (required)'), 'Kopi Corner')
    await user.click(screen.getByRole('button', { name: 'Save and continue' }))
    await waitFor(() => expect(router.state.location.pathname).toBe('/settings/telegram'))
    expect(put).toHaveBeenCalledWith(
      expect.objectContaining({ name: 'Kopi Corner', gst_rate: '9' }),
    )
    expect(await screen.findByText('Settings saved')).toBeInTheDocument()
  })
})

describe('T-033 GST rate validation', () => {
  it.each(['101', '-1'])('shows an inline error for %s and sends nothing', async (rate) => {
    const put = vi.fn()
    server.use(
      http.put('*/api/settings', () => {
        put()
        return HttpResponse.json({})
      }),
    )
    const user = userEvent.setup()
    renderApp('/settings/business')
    const field = await screen.findByLabelText('GST rate (%)')
    await user.clear(field)
    await user.type(field, rate)
    await user.click(screen.getByRole('button', { name: 'Save' }))
    expect(await screen.findByText('GST rate must be a number from 0 to 100.')).toBeInTheDocument()
    expect(field).toHaveAttribute('aria-invalid', 'true')
    expect(put).not.toHaveBeenCalled()
  })
})

describe('T-034 time validation', () => {
  it.each(['25:00', '9pm'])('rejects recap time %s and saves nothing', async (time) => {
    const put = vi.fn()
    server.use(
      http.put('*/api/settings', () => {
        put()
        return HttpResponse.json({})
      }),
    )
    const user = userEvent.setup()
    renderApp('/settings/business')
    const name = await screen.findByLabelText('Business name (required)')
    await user.clear(name)
    await user.type(name, 'Changed Name')
    const recap = screen.getByLabelText('Daily recap time')
    await user.clear(recap)
    await user.type(recap, time)
    await user.click(screen.getByRole('button', { name: 'Save' }))
    expect(await screen.findByText('Use HH:MM, for example 21:00.')).toBeInTheDocument()
    expect(put).not.toHaveBeenCalled()
  })
})

describe('T-037 business note', () => {
  it('shows the new-events note', async () => {
    renderApp('/settings/business')
    expect(await screen.findByText('Changes apply to new events only.')).toBeVisible()
  })
})

beforeEach(() => {
  setViewportWidth(1280)
})
