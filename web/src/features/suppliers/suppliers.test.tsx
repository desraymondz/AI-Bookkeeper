import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { HttpResponse, http } from 'msw'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { renderApp } from '@/test/render'
import { server } from '@/test/server'
import { setViewportWidth } from '@/test/viewport'

type SupplierRow = {
  id: number
  name: string
  uen: string | null
  default_account_id: number
  default_account_name: string
  terms_days: number
  telegram_username_hint: string | null
  active: boolean
  created_at: string
}

const accounts = [
  {
    id: 1,
    code: '5000',
    name: 'COGS Seafood',
    type: 'expense',
    subtype: 'cogs',
    active: true,
    has_postings: false,
  },
  {
    id: 2,
    code: '1000',
    name: 'Cash',
    type: 'asset',
    subtype: null,
    active: true,
    has_postings: false,
  },
]

function useSuppliersApi(rows: SupplierRow[]) {
  const posts: unknown[] = []
  server.use(
    http.get('*/api/accounts', () => HttpResponse.json(accounts)),
    http.get('*/api/suppliers', () => HttpResponse.json(rows)),
    http.post('*/api/suppliers', async ({ request }) => {
      const body = (await request.json()) as Record<string, unknown>
      posts.push(body)
      const created: SupplierRow = {
        id: 10,
        name: String(body.name),
        uen: (body.uen as string) || null,
        default_account_id: Number(body.default_account_id),
        default_account_name: 'COGS Seafood',
        terms_days: Number(body.terms_days),
        telegram_username_hint: (body.telegram_username_hint as string) || null,
        active: true,
        created_at: '2026-11-18T13:04:00Z',
      }
      rows.push(created)
      return HttpResponse.json(created, { status: 201 })
    }),
  )
  return posts
}

const ocean: SupplierRow = {
  id: 7,
  name: 'Ocean Fresh',
  uen: null,
  default_account_id: 1,
  default_account_name: 'COGS Seafood',
  terms_days: 30,
  telegram_username_hint: null,
  active: true,
  created_at: '2026-11-18T13:04:00Z',
}

beforeEach(() => setViewportWidth(1280))

describe('T-065 add supplier', () => {
  it('shows the new supplier as Active', async () => {
    useSuppliersApi([])
    const user = userEvent.setup()
    renderApp('/settings/suppliers')
    await user.click(await screen.findByRole('button', { name: 'Add supplier' }))
    const dialog = await screen.findByRole('dialog')
    await user.type(within(dialog).getByLabelText('Name (required)'), 'Ocean Fresh')
    await user.selectOptions(
      within(dialog).getByLabelText('Default account (required)'),
      'COGS Seafood',
    )
    await user.type(within(dialog).getByLabelText('UEN'), '201912345K')
    await user.clear(within(dialog).getByLabelText('Payment terms (days)'))
    await user.type(within(dialog).getByLabelText('Payment terms (days)'), '30')
    await user.type(within(dialog).getByLabelText('Telegram username hint'), '@oceanfresh')
    await user.click(within(dialog).getByRole('button', { name: 'Add supplier' }))
    const row = (await screen.findByText('Ocean Fresh')).closest('tr') as HTMLElement
    expect(within(row).getByText('Active')).toBeInTheDocument()
    expect(within(row).getByText('201912345K')).toBeInTheDocument()
    expect(within(row).getByText('@oceanfresh')).toBeInTheDocument()
  })
})

describe('T-066 required fields', () => {
  it('shows inline errors and adds nothing when name or account is empty', async () => {
    const posts = useSuppliersApi([])
    const user = userEvent.setup()
    renderApp('/settings/suppliers')
    await user.click(await screen.findByRole('button', { name: 'Add supplier' }))
    const dialog = await screen.findByRole('dialog')
    await user.click(within(dialog).getByRole('button', { name: 'Add supplier' }))
    expect(await within(dialog).findByText('Enter a supplier name.')).toBeInTheDocument()
    expect(within(dialog).getByText('Choose a default account.')).toBeInTheDocument()
    expect(posts).toHaveLength(0)
  })

  it('accepts empty UEN and Telegram hint', async () => {
    const posts = useSuppliersApi([])
    const user = userEvent.setup()
    renderApp('/settings/suppliers')
    await user.click(await screen.findByRole('button', { name: 'Add supplier' }))
    const dialog = await screen.findByRole('dialog')
    await user.type(within(dialog).getByLabelText('Name (required)'), 'Dairy Best')
    await user.selectOptions(
      within(dialog).getByLabelText('Default account (required)'),
      'COGS Seafood',
    )
    await user.click(within(dialog).getByRole('button', { name: 'Add supplier' }))
    expect(await screen.findByText('Dairy Best')).toBeInTheDocument()
    expect(posts).toHaveLength(1)
  })
})

describe('T-067 create invite', () => {
  it('shows the link, expiry in the business timezone and copies it', async () => {
    useSuppliersApi([{ ...ocean }])
    server.use(
      http.post('*/api/links/suppliers/7', () =>
        HttpResponse.json(
          {
            token: 'tok',
            url: 'https://t.me/cafe_books_bot?start=tok',
            expires_at: '2026-11-25T13:04:00Z',
          },
          { status: 201 },
        ),
      ),
    )
    const user = userEvent.setup()
    const writeText = vi.spyOn(navigator.clipboard, 'writeText').mockResolvedValue()
    renderApp('/settings/suppliers')
    await user.click(await screen.findByRole('button', { name: 'Actions for Ocean Fresh' }))
    await user.click(await screen.findByRole('menuitem', { name: 'Create invite' }))
    const dialog = await screen.findByRole('dialog')
    expect(await within(dialog).findByLabelText('Invite link')).toHaveValue(
      'https://t.me/cafe_books_bot?start=tok',
    )
    expect(within(dialog).getByText('Expires 25 Nov 2026, 21:04')).toBeInTheDocument()
    expect(within(dialog).getByText(/can be used once/)).toBeInTheDocument()
    await user.click(within(dialog).getByRole('button', { name: 'Copy link' }))
    expect(await screen.findByText('Link copied')).toBeInTheDocument()
    expect(writeText).toHaveBeenCalledWith('https://t.me/cafe_books_bot?start=tok')
  })
})
