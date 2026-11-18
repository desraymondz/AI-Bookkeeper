import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { HttpResponse, http } from 'msw'
import { beforeEach, describe, expect, it } from 'vitest'
import { renderApp } from '@/test/render'
import { server } from '@/test/server'
import { setViewportWidth } from '@/test/viewport'

beforeEach(() => {
  setViewportWidth(1280)
})

const accounts = [
  { id: 1, code: '1000', name: 'Cash', type: 'asset' },
  { id: 2, code: '1010', name: 'Bank', type: 'asset' },
  { id: 3, code: '3000', name: "Owner's Capital", type: 'equity' },
].map((a) => ({ ...a, subtype: null, active: true, has_postings: false }))

type State = {
  entry_no: string | null
  as_at: string | null
  lines: { account_id: number; debit: string; credit: string }[]
}

function useApi(state: State, puts: unknown[] = []) {
  server.use(
    http.get('*/api/accounts', () => HttpResponse.json(accounts)),
    http.get('*/api/opening-balances', () => HttpResponse.json(state)),
    http.put('*/api/opening-balances', async ({ request }) => {
      const body = await request.json()
      puts.push(body)
      return HttpResponse.json({
        entry_no: 'JE-00003',
        as_at: '2026-08-31',
        reversed_entry_no: state.entry_no,
        reversal_entry_no: state.entry_no ? 'JE-00002' : null,
      })
    }),
  )
}

const empty: State = { entry_no: null, as_at: null, lines: [] }

async function fill(user: ReturnType<typeof userEvent.setup>, capital: string) {
  await user.type(await screen.findByLabelText('As at'), '2026-08-31')
  await user.type(screen.getByLabelText('Debit for 1000 Cash'), '1000')
  await user.type(screen.getByLabelText('Debit for 1010 Bank'), '5000')
  await user.type(screen.getByLabelText("Credit for 3000 Owner's Capital"), capital)
}

describe('T-045 opening balances form', () => {
  it('shows an As at date and Debit and Credit inputs per account', async () => {
    useApi(empty)
    renderApp('/settings/opening-balances')
    expect(await screen.findByLabelText('As at')).toHaveAttribute('type', 'date')
    expect(await screen.findByLabelText('Debit for 1000 Cash')).toBeInTheDocument()
    expect(screen.getByLabelText('Credit for 1010 Bank')).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'Debit' })).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'Credit' })).toBeInTheDocument()
  })
})

describe('T-046 live difference', () => {
  it('blocks save while unbalanced', async () => {
    useApi(empty)
    const user = userEvent.setup()
    renderApp('/settings/opening-balances')
    await fill(user, '5500')
    const diff = screen.getByTestId('opening-difference')
    expect(diff).toHaveTextContent('500.00')
    expect(diff).toHaveClass('text-destructive')
    expect(screen.getByRole('button', { name: 'Save' })).toBeDisabled()
    expect(screen.getByText('Debits must equal credits.')).toBeInTheDocument()
  })

  it('saves when balanced without a dialog on first save', async () => {
    const puts: unknown[] = []
    useApi(empty, puts)
    const user = userEvent.setup()
    renderApp('/settings/opening-balances')
    await fill(user, '6000')
    await user.click(screen.getByRole('button', { name: 'Save' }))
    expect(await screen.findByText('Opening entry JE-00003 posted')).toBeInTheDocument()
    expect(puts).toEqual([
      {
        as_at: '2026-08-31',
        lines: [
          { account_id: 1, debit: '1000.00', credit: '0.00' },
          { account_id: 2, debit: '5000.00', credit: '0.00' },
          { account_id: 3, debit: '0.00', credit: '6000.00' },
        ],
      },
    ])
  })
})

describe('T-049 re-save reverses', () => {
  it('confirms before reversing the current opening entry', async () => {
    const puts: unknown[] = []
    useApi(
      {
        entry_no: 'JE-00001',
        as_at: '2026-08-31',
        lines: [
          { account_id: 1, debit: '1000.00', credit: '0.00' },
          { account_id: 3, debit: '0.00', credit: '1000.00' },
        ],
      },
      puts,
    )
    const user = userEvent.setup()
    renderApp('/settings/opening-balances')
    expect(await screen.findAllByDisplayValue('1000.00')).toHaveLength(2)
    await user.click(screen.getByRole('button', { name: 'Save' }))
    const dialog = await screen.findByRole('dialog')
    expect(
      within(dialog).getByText('This reverses JE-00001 and posts a new opening entry.'),
    ).toBeInTheDocument()
    expect(puts).toHaveLength(0)
    await user.click(within(dialog).getByRole('button', { name: 'Reverse and post' }))
    expect(await screen.findByText('Opening entry JE-00003 posted')).toBeInTheDocument()
    expect(puts).toHaveLength(1)
  })
})
