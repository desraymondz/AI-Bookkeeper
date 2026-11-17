import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { renderApp } from '@/test/render'
import { TEST_BOT_USERNAME } from '@/test/server'
import { setViewportWidth } from '@/test/viewport'

const telegramUrl = `https://t.me/${TEST_BOT_USERNAME}`

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('T-208 header Open in Telegram', () => {
  it('opens t.me/<bot username> in a new tab from the header on a signed-in page', async () => {
    setViewportWidth(1280)
    renderApp('/accounting/journal?range=this-month')

    const header = await screen.findByRole('banner')
    const link = await within(header).findByRole('link', { name: 'Open in Telegram' })

    expect(link).toHaveAttribute('href', telegramUrl)
    expect(link).toHaveAttribute('target', '_blank')
    expect(link.getAttribute('rel')).toContain('noopener')
    expect(within(header).queryByRole('button', { name: 'Open menu' })).not.toBeInTheDocument()
  })

  it.each(['/analytics?range=this-month', '/settings/business'])(
    'shows the button on %s',
    async (path) => {
      setViewportWidth(1280)
      renderApp(path)
      const header = await screen.findByRole('banner')
      expect(await within(header).findByRole('link', { name: 'Open in Telegram' })).toHaveAttribute(
        'href',
        telegramUrl,
      )
    },
  )

  it('puts the button inside the nav sheet at 375px width', async () => {
    setViewportWidth(375)
    const user = userEvent.setup()
    renderApp('/accounting/journal?range=this-month')

    const header = await screen.findByRole('banner')
    await user.click(await within(header).findByRole('button', { name: 'Open menu' }))

    const sheet = await screen.findByRole('dialog')
    const link = await within(sheet).findByRole('link', { name: 'Open in Telegram' })
    expect(link).toHaveAttribute('href', telegramUrl)
    expect(link).toHaveAttribute('target', '_blank')
    expect(link.getAttribute('rel')).toContain('noopener')
    await waitFor(() =>
      expect(within(header).queryByRole('link', { name: 'Open in Telegram' })).toBeNull(),
    )
  })
})
