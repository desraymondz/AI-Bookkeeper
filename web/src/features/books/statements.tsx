import { CheckIcon, WarningIcon } from '@phosphor-icons/react'
import type { ReactNode } from 'react'
import { ErrorState, LoadingState } from '@/components/states'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { formatMoney, isZero } from '@/lib/format'
import { cn } from '@/lib/utils'
import { type StatementLine, useBalanceSheet, usePnl, useTrialBalance } from './api'
import { RangeFilter, useRange } from './range-filter'
import { TotalsMismatch } from './totals-mismatch'

// See planning/02-design.md#accounting-page (Trial balance, P&L, Balance sheet)

type QueryLike = { isPending: boolean; isError: boolean; refetch: () => unknown }

function Frame({
  title,
  query,
  filter,
  children,
}: {
  title: string
  query: QueryLike
  filter: ReactNode
  children: ReactNode
}) {
  return (
    <section className="flex flex-col gap-4">
      <h2 className="sr-only">{title}</h2>
      {filter}
      {query.isPending ? <LoadingState /> : null}
      {query.isError ? (
        <ErrorState
          message={`Could not load the ${title.toLowerCase()}.`}
          onRetry={() => void query.refetch()}
        />
      ) : null}
      {children}
    </section>
  )
}

export function TrialBalancePage() {
  const search = useRange()
  const tb = useTrialBalance(search)
  const data = tb.data
  return (
    <Frame
      title="Trial balance"
      query={tb}
      filter={<RangeFilter start={data?.as_at} end={data?.as_at} asAt />}
    >
      {data ? (
        <>
          <TotalsMismatch debit={data.total_debit} credit={data.total_credit} />
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Code</TableHead>
                <TableHead>Account</TableHead>
                <TableHead className="text-right">Debit</TableHead>
                <TableHead className="text-right">Credit</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.rows.map((row) => (
                <TableRow key={row.account_id}>
                  <TableCell>{row.code}</TableCell>
                  <TableCell>{row.name}</TableCell>
                  <TableCell className="text-right tabular-nums">
                    {isZero(row.debit) ? '' : formatMoney(row.debit)}
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {isZero(row.credit) ? '' : formatMoney(row.credit)}
                  </TableCell>
                </TableRow>
              ))}
              <TableRow className="font-semibold">
                <TableCell colSpan={2}>Total</TableCell>
                <TableCell className="text-right tabular-nums" data-testid="total-debit">
                  {formatMoney(data.total_debit)}
                </TableCell>
                <TableCell className="text-right tabular-nums" data-testid="total-credit">
                  {formatMoney(data.total_credit)}
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </>
      ) : null}
    </Frame>
  )
}

function Heading({ children }: { children: ReactNode }) {
  return (
    <TableRow>
      <TableCell colSpan={2} className="pt-4 font-semibold">
        {children}
      </TableCell>
    </TableRow>
  )
}

function Lines({ lines }: { lines: StatementLine[] }) {
  return lines.map((line) => (
    <TableRow key={`${line.code ?? ''}-${line.name}`}>
      <TableCell className="pl-7">{line.name}</TableCell>
      <TableCell className="text-right tabular-nums">{formatMoney(line.amount)}</TableCell>
    </TableRow>
  ))
}

function Total({
  label,
  amount,
  final = false,
}: {
  label: string
  amount: string
  final?: boolean
}) {
  return (
    <TableRow className="font-semibold">
      <TableCell>{label}</TableCell>
      <TableCell
        className={cn(
          'border-t border-foreground text-right tabular-nums',
          final && 'border-b-[3px] border-b-foreground border-double',
        )}
      >
        {formatMoney(amount)}
      </TableCell>
    </TableRow>
  )
}

function StatementTable({ children }: { children: ReactNode }) {
  return (
    <Table className="max-w-2xl">
      <TableHeader>
        <TableRow>
          <TableHead>Line</TableHead>
          <TableHead className="text-right">Amount (SGD)</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>{children}</TableBody>
    </Table>
  )
}

export function PnlPage() {
  const search = useRange()
  const pnl = usePnl(search)
  const data = pnl.data
  return (
    <Frame title="P&L" query={pnl} filter={<RangeFilter start={data?.start} end={data?.end} />}>
      {data ? (
        <StatementTable>
          <Heading>Revenue</Heading>
          <Lines lines={data.revenue} />
          <Total label="Total revenue" amount={data.total_revenue} />
          <Heading>COGS</Heading>
          <Lines lines={data.cogs} />
          <Total label="Total COGS" amount={data.total_cogs} />
          <Total label="Gross profit" amount={data.gross_profit} />
          <Heading>Operating expenses</Heading>
          <Lines lines={data.operating_expenses} />
          <Total label="Total operating expenses" amount={data.total_operating_expenses} />
          <Total label="Operating profit" amount={data.operating_profit} />
          <Heading>Other items</Heading>
          <Lines lines={data.other_items} />
          <Total label="Total other items" amount={data.total_other_items} />
          <Total label="Net profit" amount={data.net_profit} final />
        </StatementTable>
      ) : null}
    </Frame>
  )
}

export function BalanceSheetPage() {
  const search = useRange()
  const bs = useBalanceSheet(search)
  const data = bs.data
  return (
    <Frame
      title="Balance sheet"
      query={bs}
      filter={<RangeFilter start={data?.as_at} end={data?.as_at} asAt />}
    >
      {data ? (
        <>
          <StatementTable>
            <Heading>Assets</Heading>
            <Lines lines={data.current_assets} />
            <Lines lines={data.fixed_assets} />
            <Total label="Total assets" amount={data.total_assets} />
            <Heading>Liabilities</Heading>
            <Lines lines={data.liabilities} />
            <Total label="Total liabilities" amount={data.total_liabilities} />
            <Heading>Equity</Heading>
            <Lines lines={data.equity} />
            <Total label="Total equity" amount={data.total_equity} />
            <Total
              label="Total liabilities and equity"
              amount={data.total_liabilities_and_equity}
              final
            />
          </StatementTable>
          <p className="flex items-center gap-2 text-sm" data-testid="bs-check">
            Assets = Liabilities + Equity:
            {data.balanced ? (
              <span className="inline-flex items-center gap-1 font-semibold">
                <CheckIcon aria-hidden className="size-4" />
                Balanced
              </span>
            ) : (
              <span role="alert" className="inline-flex items-center gap-1 text-destructive">
                <WarningIcon aria-hidden className="size-4" />
                Difference {formatMoney(data.difference)}
              </span>
            )}
          </p>
        </>
      ) : null}
    </Frame>
  )
}
