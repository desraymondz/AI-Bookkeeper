import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { HttpResponse, http } from 'msw'
import { beforeEach, describe, expect, it } from 'vitest'
import { renderApp } from '@/test/render'
import { server } from '@/test/server'
import { setViewportWidth } from '@/test/viewport'

// See planning/04-test-spec.md T-022, T-183, T-185, T-187 to T-189, T-191, T-195, T-199, T-200

const RANGES: Record<string, [string, string]> = {
  this_month: ['2026-11-01', '2026-11-18'],
  last_month: ['2026-10-01', '2026-10-31'],
  last_3_months: ['2026-09-01', '2026-11-18'],
  ytd: ['2026-04-01', '2026-11-18'],
  last_12_months: ['2025-12-01', '2026-11-18'],
}

function line(no: number, code: string, name: string, debit: string, credit: string) {
  return {
    line_no: no,
    account_id: no,
    account_code: code,
    account_name: name,
    memo: null,
    debit,
    credit,
  }
}

function entry(n: number, date: string, source: string, kind = 'normal') {
  return {
    id: n,
    entry_no: `JE-${String(n).padStart(5, '0')}`,
    date,
    description: `Entry ${n}`,
    source,
    kind,
    status: 'posted',
    note: null,
    lines: [
      line(1, '5000', 'COGS Seafood', '400.00', '0.00'),
      line(2, '2000', 'Accounts Payable', '0.00', '400.00'),
    ],
    total_debit: '400.00',
    total_credit: '400.00',
  }
}

const ENTRIES = [
  entry(1, '2026-11-02', 'auto'),
  entry(2, '2026-11-03', 'boss_approved'),
  entry(3, '2026-11-04', 'manual'),
  entry(4, '2026-11-05', 'system', 'adjusting'),
  entry(5, '2026-11-06', 'system', 'opening'),
  entry(6, '2026-11-07', 'boss_approved', 'reversal'),
  entry(7, '2026-10-15', 'auto'),
]

function detail(n: number, withChecks: boolean) {
  const base = ENTRIES[n - 1] ?? entry(n, '2026-11-02', 'auto')
  return {
    ...base,
    checks: withChecks
      ? [
          { check_code: 'gst', passed: true, detail: null },
          { check_code: 'price_change', passed: false, detail: 'Unit price 29.50, last 28.00' },
        ]
      : [],
    document: withChecks
      ? { document_id: 9, invoice_id: 3, mime: 'application/pdf', kind: 'invoice' }
      : null,
    audit: [{ at: '2026-11-18T13:04:00Z', actor: 'agent', action: 'entry.posted', detail: {} }],
    reverses: null,
    reversed_by: withChecks ? { id: 6, entry_no: 'JE-00006' } : null,
  }
}

function useBooksApi() {
  server.use(
    http.get('*/api/journal', ({ request }) => {
      const preset = new URL(request.url).searchParams.get('preset') ?? 'this_month'
      const [start, end] = RANGES[preset] ?? RANGES.this_month
      const entries = ENTRIES.filter((e) => e.date >= start && e.date <= end)
      const total = `${entries.length * 400}.00`
      return HttpResponse.json({ start, end, entries, total_debit: total, total_credit: total })
    }),
    http.get('*/api/journal/:no', ({ params }) => {
      const n = Number(String(params.no).replace('JE-', ''))
      return HttpResponse.json(detail(n, n === 1))
    }),
    http.get('*/api/reports/trial-balance', () =>
      HttpResponse.json({
        as_at: '2026-11-30',
        rows: [
          {
            account_id: 1,
            code: '1010',
            name: 'Bank',
            type: 'asset',
            debit: '5000.00',
            credit: '0.00',
          },
          {
            account_id: 2,
            code: '3000',
            name: "Owner's Capital",
            type: 'equity',
            debit: '0.00',
            credit: '5000.00',
          },
        ],
        total_debit: '5000.00',
        total_credit: '5000.00',
        difference: '0.00',
      }),
    ),
    http.get('*/api/reports/pnl', () =>
      HttpResponse.json({
        start: '2026-10-01',
        end: '2026-10-31',
        revenue: [{ account_id: 1, code: '4000', name: 'Sales', amount: '52310.40' }],
        total_revenue: '52310.40',
        cogs: [{ account_id: 2, code: '5000', name: 'COGS Seafood', amount: '12000.00' }],
        total_cogs: '12000.00',
        gross_profit: '40310.40',
        operating_expenses: [{ account_id: 3, code: '6000', name: 'Rent', amount: '8000.00' }],
        total_operating_expenses: '8000.00',
        operating_profit: '32310.40',
        other_items: [],
        total_other_items: '0.00',
        net_profit: '32310.40',
      }),
    ),
    http.get('*/api/reports/balance-sheet', () =>
      HttpResponse.json({
        as_at: '2026-11-18',
        current_assets: [{ account_id: 1, code: '1010', name: 'Bank', amount: '5000.00' }],
        total_current_assets: '5000.00',
        fixed_assets: [],
        total_fixed_assets: '0.00',
        total_assets: '5000.00',
        liabilities: [],
        total_liabilities: '0.00',
        equity: [{ account_id: 2, code: '3000', name: "Owner's Capital", amount: '5000.00' }],
        total_equity: '5000.00',
        total_liabilities_and_equity: '5000.00',
        difference: '0.00',
        balanced: true,
      }),
    ),
  )
}

beforeEach(() => {
  setViewportWidth(1280)
  useBooksApi()
})

describe('T-183 journal columns and source badges', () => {
  it('shows the columns and a badge per source', async () => {
    renderApp('/accounting/journal?range=this-month')
    await screen.findByText('JE-00001')
    const headers = screen.getAllByRole('columnheader').map((h) => h.textContent)
    expect(headers).toEqual([
      'Date',
      'Entry no.',
      'Description',
      'Account',
      'Debit',
      'Credit',
      'Source',
      'Status',
    ])
    for (const label of ['Auto', 'Approved', 'Manual', 'Adjusting', 'Opening', 'Reversal']) {
      expect(screen.getByText(label)).toBeInTheDocument()
    }
  })
})

describe('T-185 T-187 presets', () => {
  it('updates the URL, label and rows for each preset', async () => {
    const user = userEvent.setup()
    const { router } = renderApp('/accounting/journal?range=this-month')
    await screen.findByText('JE-00001')
    await user.selectOptions(screen.getByLabelText('Date range'), 'last-month')
    await waitFor(() => expect(router.state.location.search).toMatchObject({ range: 'last-month' }))
    await waitFor(() =>
      expect(screen.getByTestId('range-label')).toHaveTextContent('Last month: 1 to 31 Oct 2026'),
    )
    expect(screen.getByText('JE-00007')).toBeInTheDocument()
    expect(screen.queryByText('JE-00001')).not.toBeInTheDocument()
    await user.selectOptions(screen.getByLabelText('Date range'), 'year-to-date')
    await waitFor(() =>
      expect(screen.getByTestId('range-label')).toHaveTextContent(
        'Year to date: 1 Apr 2026 to 18 Nov 2026',
      ),
    )
  })
})

describe('T-191 totals', () => {
  it('shows equal debit and credit totals', async () => {
    renderApp('/accounting/journal?range=this-month')
    await screen.findByText('JE-00001')
    expect(screen.getByTestId('total-debit')).toHaveTextContent('2,400.00')
    expect(screen.getByTestId('total-credit')).toHaveTextContent('2,400.00')
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })
})

describe('T-188 T-189 entry sheet', () => {
  it('opens at the entry URL with lines, failed checks first, document, reversal and audit', async () => {
    const user = userEvent.setup()
    const { router } = renderApp('/accounting/journal?range=this-month')
    await user.click(await screen.findByRole('button', { name: 'JE-00001' }))
    await waitFor(() => expect(router.state.location.pathname).toBe('/accounting/journal/JE-00001'))
    const sheet = await screen.findByRole('dialog')
    await within(sheet).findByText('Lines')
    const checks = within(sheet).getByRole('list', { name: 'Checks' })
    const names = within(checks)
      .getAllByRole('listitem')
      .map((item) => item.textContent ?? '')
    expect(names[0]).toContain('Price change')
    expect(names[1]).toContain('GST')
    expect(within(sheet).getByTitle('Invoice document')).toHaveAttribute(
      'src',
      '/api/documents/9/file',
    )
    expect(within(sheet).getByText('Reversed by JE-00006')).toBeInTheDocument()
    expect(within(sheet).getByText('18 Nov 2026, 21:04')).toBeInTheDocument()
  })

  it('shows no checks text and hides the document for a manual entry', async () => {
    renderApp('/accounting/journal/JE-00003?range=this-month')
    const sheet = await screen.findByRole('dialog')
    expect(
      await within(sheet).findByText('No automated checks for manual entries.'),
    ).toBeInTheDocument()
    expect(within(sheet).queryByText('Document')).not.toBeInTheDocument()
  })
})

describe('T-195 trial balance', () => {
  it('labels as at the range end and shows equal totals', async () => {
    renderApp('/accounting/trial-balance?range=this-month')
    await screen.findByText('Bank')
    expect(screen.getByTestId('range-label')).toHaveTextContent('As at 30 Nov 2026')
    expect(screen.getByTestId('total-debit')).toHaveTextContent('5,000.00')
    expect(screen.getByTestId('total-credit')).toHaveTextContent('5,000.00')
  })
})

describe('T-199 P&L', () => {
  it('shows each section and consistent profit lines', async () => {
    renderApp('/accounting/pnl?range=last-month')
    await screen.findByText('Total revenue')
    for (const label of [
      'Revenue',
      'COGS',
      'Gross profit',
      'Operating expenses',
      'Operating profit',
      'Other items',
      'Net profit',
    ]) {
      expect(screen.getByText(label)).toBeInTheDocument()
    }
    const gross = screen.getByText('Gross profit').closest('tr') as HTMLElement
    expect(within(gross).getByText('40,310.40')).toBeInTheDocument()
  })
})

describe('T-200 balance sheet', () => {
  it('shows the sections and the Balanced check line', async () => {
    renderApp('/accounting/balance-sheet?range=this-month')
    await screen.findByText('Total assets')
    for (const label of ['Assets', 'Liabilities', 'Equity']) {
      expect(screen.getByText(label)).toBeInTheDocument()
    }
    expect(screen.getByTestId('bs-check')).toHaveTextContent(
      'Assets = Liabilities + Equity:Balanced',
    )
  })
})

describe('T-022 read-only books', () => {
  it('has no edit, delete or add controls on the tabs and the sheet', async () => {
    for (const path of [
      '/accounting/journal?range=this-month',
      '/accounting/trial-balance',
      '/accounting/pnl',
      '/accounting/balance-sheet',
      '/accounting/journal/JE-00001',
    ]) {
      const view = renderApp(path)
      await waitFor(() => expect(screen.queryAllByRole('status')).toHaveLength(0))
      const main = view.container.ownerDocument.body
      const buttons = within(main)
        .queryAllByRole('button')
        .map((b) => (b.textContent ?? '').trim().toLowerCase())
      for (const word of ['edit', 'delete', 'add', 'new', 'remove']) {
        expect(buttons.some((label) => label.startsWith(word))).toBe(false)
      }
      view.unmount()
    }
  })
})
