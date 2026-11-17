import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { HttpResponse, http } from 'msw'
import { beforeEach, describe, expect, it } from 'vitest'
import { renderApp } from '@/test/render'
import { server } from '@/test/server'
import { setViewportWidth } from '@/test/viewport'

type UserRow = {
  id: number
  display_name: string | null
  username: string | null
  role: 'boss' | 'supplier'
  supplier_id: number | null
  supplier_name: string | null
  status: 'active' | 'deactivated' | 'blocked'
  linked_at: string | null
}

function supplier(id: number, name: string) {
  return {
    id,
    name,
    uen: null,
    default_account_id: 1,
    default_account_name: 'COGS Seafood',
    terms_days: 30,
    telegram_username_hint: null,
    active: true,
    created_at: '2026-11-01T00:00:00Z',
  }
}

function makeRows(): UserRow[] {
  return [
    {
      id: 1,
      display_name: 'Mei Tan',
      username: 'meitan',
      role: 'boss',
      supplier_id: null,
      supplier_name: null,
      status: 'active',
      linked_at: '2026-11-02T04:00:00Z',
    },
    {
      id: 2,
      display_name: 'Ocean Rep',
      username: 'oceanrep',
      role: 'supplier',
      supplier_id: 7,
      supplier_name: 'Ocean Fresh',
      status: 'active',
      linked_at: '2026-11-03T04:00:00Z',
    },
    {
      id: 3,
      display_name: 'Dairy Rep',
      username: 'dairyrep',
      role: 'supplier',
      supplier_id: 8,
      supplier_name: 'Dairy Best',
      status: 'active',
      linked_at: '2026-11-04T04:00:00Z',
    },
  ]
}

function useUsersApi(rows: UserRow[]) {
  server.use(
    http.get('*/api/suppliers', () =>
      HttpResponse.json([supplier(7, 'Ocean Fresh'), supplier(8, 'Dairy Best')]),
    ),
    http.get('*/api/users', () => HttpResponse.json(rows)),
    http.patch('*/api/users/:id', async ({ params, request }) => {
      const body = (await request.json()) as { supplier_id?: number; status?: UserRow['status'] }
      const row = rows.find((item) => item.id === Number(params.id)) as UserRow
      if (body.supplier_id) {
        row.supplier_id = body.supplier_id
        row.supplier_name = body.supplier_id === 8 ? 'Dairy Best' : 'Ocean Fresh'
      }
      if (body.status) row.status = body.status
      return HttpResponse.json(row)
    }),
  )
}

beforeEach(() => setViewportWidth(1280))

describe('T-071 users table', () => {
  it('shows name, username, role, supplier, status and linked date per row', async () => {
    useUsersApi(makeRows())
    renderApp('/settings/users')
    const boss = (await screen.findByText('Mei Tan')).closest('tr') as HTMLElement
    expect(within(boss).getByText('@meitan')).toBeInTheDocument()
    expect(within(boss).getByText('Boss')).toBeInTheDocument()
    expect(within(boss).getByText('2 Nov 2026')).toBeInTheDocument()
    const ocean = screen.getByText('Ocean Rep').closest('tr') as HTMLElement
    expect(within(ocean).getByText('Supplier')).toBeInTheDocument()
    expect(within(ocean).getByText('Ocean Fresh')).toBeInTheDocument()
    expect(within(ocean).getByText('Active')).toBeInTheDocument()
    expect(within(ocean).getByText('3 Nov 2026')).toBeInTheDocument()
    const dairy = screen.getByText('Dairy Rep').closest('tr') as HTMLElement
    expect(within(dairy).getByText('Dairy Best')).toBeInTheDocument()
  })
})

describe('T-072 change linked supplier', () => {
  it('shows the picked supplier on the row', async () => {
    useUsersApi(makeRows())
    const user = userEvent.setup()
    renderApp('/settings/users')
    await user.click(await screen.findByRole('button', { name: 'Actions for Ocean Rep' }))
    await user.click(await screen.findByRole('menuitem', { name: 'Change linked supplier' }))
    const dialog = await screen.findByRole('dialog')
    await waitFor(() =>
      expect(within(dialog).getByRole('option', { name: 'Dairy Best' })).toBeInTheDocument(),
    )
    await user.selectOptions(within(dialog).getByLabelText('Supplier'), 'Dairy Best')
    await user.click(within(dialog).getByRole('button', { name: 'Save' }))
    await waitFor(() => {
      const row = screen.getByText('Ocean Rep').closest('tr') as HTMLElement
      expect(within(row).getByText('Dairy Best')).toBeInTheDocument()
    })
  })
})

describe('T-073 deactivate and revoke', () => {
  it('shows Deactivated after confirming Deactivate', async () => {
    useUsersApi(makeRows())
    const user = userEvent.setup()
    renderApp('/settings/users')
    await user.click(await screen.findByRole('button', { name: 'Actions for Ocean Rep' }))
    await user.click(await screen.findByRole('menuitem', { name: 'Deactivate' }))
    const dialog = await screen.findByRole('dialog')
    await user.click(within(dialog).getByRole('button', { name: 'Deactivate' }))
    await waitFor(() => {
      const row = screen.getByText('Ocean Rep').closest('tr') as HTMLElement
      expect(within(row).getByText('Deactivated')).toBeInTheDocument()
    })
  })

  it('keeps the row with the new status after confirming Revoke link', async () => {
    const rows = makeRows()
    useUsersApi(rows)
    server.use(
      http.post('*/api/users/:id/revoke', ({ params }) => {
        const row = rows.find((item) => item.id === Number(params.id)) as UserRow
        row.status = 'deactivated'
        return HttpResponse.json(row)
      }),
    )
    const user = userEvent.setup()
    renderApp('/settings/users')
    await user.click(await screen.findByRole('button', { name: 'Actions for Ocean Rep' }))
    await user.click(await screen.findByRole('menuitem', { name: 'Revoke link' }))
    const dialog = await screen.findByRole('dialog')
    await user.click(within(dialog).getByRole('button', { name: 'Revoke link' }))
    await waitFor(() => {
      const row = screen.getByText('Ocean Rep').closest('tr') as HTMLElement
      expect(within(row).getByText('Deactivated')).toBeInTheDocument()
    })
  })
})

describe('T-074 boss row', () => {
  it('has no destructive actions and shows the single boss note', async () => {
    useUsersApi(makeRows())
    const user = userEvent.setup()
    renderApp('/settings/users')
    await user.click(await screen.findByRole('button', { name: 'Actions for Mei Tan' }))
    await screen.findByRole('menu')
    expect(screen.queryByRole('menuitem', { name: /deactivate|revoke/i })).not.toBeInTheDocument()
    expect(screen.getByText('There is exactly one boss.')).toBeInTheDocument()
  })
})
