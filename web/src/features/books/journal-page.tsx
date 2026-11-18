import { useNavigate } from '@tanstack/react-router'
import { Fragment } from 'react'
import { EmptyState, ErrorState, TableLoadingRows } from '@/components/states'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { formatDate, formatMoney, isZero } from '@/lib/format'
import { useJournal } from './api'
import { SourceBadge, StatusBadge } from './badges'
import { RangeFilter, useRange } from './range-filter'
import { TotalsMismatch } from './totals-mismatch'

// See planning/02-design.md#accounting-page (Journal) and planning/01-prd.md#f-024

const COLUMNS = [
  'Date',
  'Entry no.',
  'Description',
  'Account',
  'Debit',
  'Credit',
  'Source',
  'Status',
]

export function JournalPage() {
  const search = useRange()
  const navigate = useNavigate()
  const journal = useJournal(search)
  const data = journal.data

  function open(entryNo: string) {
    void navigate({ to: '/accounting/journal/$entryNo', params: { entryNo }, search })
  }

  return (
    <section className="flex flex-col gap-4">
      <h2 className="sr-only">Journal</h2>
      <RangeFilter start={data?.start} end={data?.end} />
      {journal.isError ? (
        <ErrorState message="Could not load the journal." onRetry={() => void journal.refetch()} />
      ) : (
        <>
          {data ? <TotalsMismatch debit={data.total_debit} credit={data.total_credit} /> : null}
          <Table>
            <TableHeader>
              <TableRow>
                {COLUMNS.map((c) => (
                  <TableHead
                    key={c}
                    className={c === 'Debit' || c === 'Credit' ? 'text-right' : undefined}
                  >
                    {c}
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {journal.isPending ? <TableLoadingRows columns={COLUMNS.length} /> : null}
              {data && data.entries.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={COLUMNS.length}>
                    <EmptyState message="No entries in this range." className="py-2" />
                  </TableCell>
                </TableRow>
              ) : null}
              {data?.entries.map((entry) => (
                <Fragment key={entry.id}>
                  {entry.lines.map((line, index) => (
                    <TableRow
                      key={`${entry.id}-${line.line_no}`}
                      data-entry={entry.entry_no}
                      className={
                        index === 0
                          ? 'cursor-pointer border-t border-foreground/20'
                          : 'cursor-pointer'
                      }
                      onClick={() => open(entry.entry_no)}
                    >
                      <TableCell>{index === 0 ? formatDate(entry.date) : null}</TableCell>
                      <TableCell>
                        {index === 0 ? (
                          <button
                            type="button"
                            className="underline-offset-2 hover:underline"
                            onClick={(event) => {
                              event.stopPropagation()
                              open(entry.entry_no)
                            }}
                          >
                            {entry.entry_no}
                          </button>
                        ) : null}
                      </TableCell>
                      <TableCell>{index === 0 ? entry.description : null}</TableCell>
                      <TableCell>
                        {line.account_code} {line.account_name}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {isZero(line.debit) ? '' : formatMoney(line.debit)}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {isZero(line.credit) ? '' : formatMoney(line.credit)}
                      </TableCell>
                      <TableCell>
                        {index === 0 ? (
                          <SourceBadge source={entry.source} kind={entry.kind} />
                        ) : null}
                      </TableCell>
                      <TableCell>
                        {index === 0 ? <StatusBadge status={entry.status} /> : null}
                      </TableCell>
                    </TableRow>
                  ))}
                </Fragment>
              ))}
              {data ? (
                <TableRow className="font-semibold">
                  <TableCell colSpan={4}>Total</TableCell>
                  <TableCell className="text-right tabular-nums" data-testid="total-debit">
                    {formatMoney(data.total_debit)}
                  </TableCell>
                  <TableCell className="text-right tabular-nums" data-testid="total-credit">
                    {formatMoney(data.total_credit)}
                  </TableCell>
                  <TableCell colSpan={2} />
                </TableRow>
              ) : null}
            </TableBody>
          </Table>
        </>
      )}
    </section>
  )
}
