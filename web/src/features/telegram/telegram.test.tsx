import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { HttpResponse, http } from 'msw'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { renderApp } from '@/test/render'
import { server } from '@/test/server'
import { setViewportWidth } from '@/test/viewport'

const disconnected = { connected: false, username: null, display_name: null, linked_at: null }
const connected = {
  connected: true,
  username: 'meitan',
  display_name: 'Mei Tan',
  linked_at: '2026-11-02T04:00:00Z',
}
const link = {
  token: 'tok',
  url: 'https://t.me/cafe_books_bot?start=tok',
  expires_at: '2026-11-19T13:04:00Z',
}

beforeEach(() => setViewportWidth(1280))

describe('T-057 connect Telegram', () => {
  it('shows link, Copy, Open in Telegram, QR code and expiry after Connect Telegram', async () => {
    const posted = vi.fn()
    server.use(
      http.get('*/api/links/boss', () => HttpResponse.json(disconnected)),
      http.post('*/api/links/boss', () => {
        posted()
        return HttpResponse.json(link, { status: 201 })
      }),
    )
    const user = userEvent.setup()
    renderApp('/settings/telegram')
    expect(await screen.findByText('Not connected')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Connect Telegram' }))
    const input = await screen.findByLabelText('Telegram link')
    expect(input).toHaveValue(link.url)
    expect(input).toHaveAttribute('readonly')
    expect(screen.getByRole('button', { name: 'Copy' })).toBeInTheDocument()
    const links = screen.getAllByRole('link', { name: 'Open in Telegram' })
    expect(links.some((item) => item.getAttribute('href') === link.url)).toBe(true)
    expect(screen.getByRole('img', { name: 'QR code' })).toBeInTheDocument()
    expect(screen.getByText('Expires 19 Nov 2026, 21:04')).toBeInTheDocument()
    expect(posted).toHaveBeenCalledTimes(1)
  })
})

describe('T-063 reconnect', () => {
  it('warns in a dialog before a new token is made', async () => {
    const posted = vi.fn()
    server.use(
      http.get('*/api/links/boss', () => HttpResponse.json(connected)),
      http.post('*/api/links/boss', () => {
        posted()
        return HttpResponse.json(link, { status: 201 })
      }),
    )
    const user = userEvent.setup()
    renderApp('/settings/telegram')
    expect(await screen.findByText('Connected as @meitan')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Reconnect' }))
    const dialog = await screen.findByRole('dialog')
    expect(
      within(dialog).getByText('Your current Telegram account will be disconnected.'),
    ).toBeInTheDocument()
    expect(posted).not.toHaveBeenCalled()
    await user.click(within(dialog).getByRole('button', { name: 'Create new link' }))
    await waitFor(() => expect(posted).toHaveBeenCalledTimes(1))
    expect(await screen.findByLabelText('Telegram link')).toHaveValue(link.url)
  })
})
