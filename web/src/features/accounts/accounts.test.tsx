import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { HttpResponse, http } from 'msw'
import { beforeEach, describe, expect, it } from 'vitest'
import { renderApp } from '@/test/render'
import { server } from '@/test/server'
import { setViewportWidth } from '@/test/viewport'

type Row = {
  id: number
  code: string
  name: string
  type: string
  subtype: string | null
  active: boolean
  has_postings: boolean
}

const seafood: Row = {
  id: 1,
  code: '5000',
  name: 'COGS Seafood',
  type: 'expense',
  subtype: 'cogs',
  active: true,
  has_postings: true,
}
const spare: Row = { ...seafood, id: 2, code: '6900', name: 'Spare', has_postings: false }

function useAccountsApi(rows: Row[]) {
  server.use(
    http.get('*/api/accounts', () => HttpResponse.json(rows)),
    http.post('*/api/accounts', async ({ request }) => {
      const body = (await request.json()) as Pick<Row, 'code' | 'name' | 'type'>
      if (rows.some((row) => row.code === body.code)) {
        return HttpResponse.json(
          {
            detail: [
              { loc: ['body', 'code'], msg: 'Account code already exists', type: 'duplicate' },
            ],
          },
          { status: 409 },
        )
      }
      const created = { ...body, id: 99, subtype: null, active: true, has_postings: false }
      rows.push(created)
      return HttpResponse.json(created, { status: 201 })
    }),
    http.patch('*/api/accounts/:id', async ({ params, request }) => {
      const body = (await request.json()) as { active: boolean }
      const row = rows.find((item) => item.id === Number(params.id))
      if (!row) return HttpResponse.json({}, { status: 404 })
      row.active = body.active
      return HttpResponse.json(row)
    }),
  )
}

async function addAccount(user: ReturnType<typeof userEvent.setup>, code: string, name: string) {
  await user.click(await screen.findByRole('button', { name: 'Add account' }))
  const dialog = await screen.findByRole('dialog')
  await user.type(within(dialog).getByLabelText('Code (required)'), code)
  await user.type(within(dialog).getByLabelText('Name (required)'), name)
  await user.selectOptions(within(dialog).getByLabelText('Type'), 'Expense')
  await user.click(within(dialog).getByRole('button', { name: 'Add account' }))
}

describe('T-039 add account', () => {
  it('shows the new account as Active', async () => {
    useAccountsApi([{ ...seafood }])
    const user = userEvent.setup()
    renderApp('/settings/accounts')
    await addAccount(user, '6100', 'Ice')
    const row = (await screen.findByText('Ice')).closest('tr')
    expect(row).not.toBeNull()
    expect(within(row as HTMLElement).getByText('Active')).toBeInTheDocument()
  })
})

describe('T-040 duplicate code', () => {
  it('shows an inline error and adds nothing', async () => {
    useAccountsApi([{ ...seafood }])
    const user = userEvent.setup()
    renderApp('/settings/accounts')
    await addAccount(user, '5000', 'Another')
    expect(await screen.findByText(/already used/)).toBeInTheDocument()
    expect(screen.queryByText('Another')).not.toBeInTheDocument()
  })
})

describe('T-041 deactivate', () => {
  it('hides inactive accounts unless Show inactive is on', async () => {
    useAccountsApi([{ ...seafood }, { ...spare }])
    const user = userEvent.setup()
    renderApp('/settings/accounts')
    await user.click(await screen.findByRole('button', { name: 'Actions for 6900 Spare' }))
    await user.click(await screen.findByRole('menuitem', { name: 'Deactivate' }))
    await screen.findByText('COGS Seafood')
    expect(screen.queryByText('Spare')).not.toBeInTheDocument()
    await user.click(screen.getByRole('switch', { name: 'Show inactive' }))
    const row = (await screen.findByText('Spare')).closest('tr') as HTMLElement
    expect(within(row).getByText('Inactive')).toBeInTheDocument()
  })
})

describe('T-042 accounts with postings', () => {
  it('disables Deactivate with the Has postings tooltip', async () => {
    useAccountsApi([{ ...seafood }])
    const user = userEvent.setup()
    renderApp('/settings/accounts')
    await user.click(await screen.findByRole('button', { name: 'Actions for 5000 COGS Seafood' }))
    const item = await screen.findByRole('menuitem', { name: 'Deactivate' })
    expect(item).toHaveAttribute('aria-disabled', 'true')
    expect(screen.queryByRole('menuitem', { name: /delete|type/i })).not.toBeInTheDocument()
    await user.hover(item.parentElement as HTMLElement)
    expect((await screen.findAllByText('Has postings')).length).toBeGreaterThan(0)
  })
})

beforeEach(() => {
  setViewportWidth(1280)
})
