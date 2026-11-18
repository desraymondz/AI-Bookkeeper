import {
  ArrowSquareOutIcon,
  ArrowsCounterClockwiseIcon,
  CheckIcon,
  XIcon,
} from '@phosphor-icons/react'
import { Link, useNavigate } from '@tanstack/react-router'
import { ErrorState, LoadingState } from '@/components/states'
import { Badge } from '@/components/ui/badge'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { ApiError } from '@/lib/api'
import { formatDate, formatMoney, formatTimestamp, isZero } from '@/lib/format'
import { documentUrl, type JournalEntryDetail, useEntry } from './api'
import { SourceBadge, StatusBadge } from './badges'
import { useRange } from './range-filter'

// See planning/02-design.md#entry-detail-sheet-f-0243

const CHECK_NAMES: Record<string, string> = {
  known_supplier: 'Known supplier',
  arithmetic: 'Arithmetic',
  gst: 'GST',
  balanced: 'Balanced',
  duplicate: 'Duplicate',
  revision: 'Revision',
  price_change: 'Price change',
  period: 'Period',
  sanity: 'Sanity',
  suspicious: 'Suspicious content',
}

const ACTORS: Record<string, string> = { agent: 'Agent', boss: 'Boss', system: 'System' }

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="flex flex-col gap-2 border-t pt-4">
      <h3 className="text-lg font-semibold">{title}</h3>
      {children}
    </section>
  )
}

function Lines({ entry }: { entry: JournalEntryDetail }) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Account</TableHead>
          <TableHead>Memo</TableHead>
          <TableHead className="text-right">Debit</TableHead>
          <TableHead className="text-right">Credit</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {entry.lines.map((line) => (
          <TableRow key={line.line_no}>
            <TableCell>
              {line.account_code} {line.account_name}
            </TableCell>
            <TableCell>{line.memo ?? ''}</TableCell>
            <TableCell className="text-right tabular-nums">
              {isZero(line.debit) ? '' : formatMoney(line.debit)}
            </TableCell>
            <TableCell className="text-right tabular-nums">
              {isZero(line.credit) ? '' : formatMoney(line.credit)}
            </TableCell>
          </TableRow>
        ))}
        <TableRow className="font-semibold">
          <TableCell colSpan={2}>Total</TableCell>
          <TableCell className="text-right tabular-nums">
            {formatMoney(entry.total_debit)}
          </TableCell>
          <TableCell className="text-right tabular-nums">
            {formatMoney(entry.total_credit)}
          </TableCell>
        </TableRow>
      </TableBody>
    </Table>
  )
}

function Checks({ entry }: { entry: JournalEntryDetail }) {
  if (entry.checks.length === 0) {
    return <p className="text-sm text-muted-foreground">No automated checks for manual entries.</p>
  }
  const ordered = [...entry.checks].sort((a, b) => Number(a.passed) - Number(b.passed))
  return (
    <ul className="flex flex-col gap-2" aria-label="Checks">
      {ordered.map((check) => (
        <li key={check.check_code} className="flex flex-wrap items-center gap-2 text-sm">
          <span className="min-w-36 font-medium">
            {CHECK_NAMES[check.check_code] ?? check.check_code}
          </span>
          {check.passed ? (
            <Badge variant="outline">
              <CheckIcon aria-hidden className="mr-1 size-3" />
              Pass
            </Badge>
          ) : (
            <Badge variant="filled">
              <XIcon aria-hidden className="mr-1 size-3" />
              Fail
            </Badge>
          )}
          {check.detail ? <span className="text-muted-foreground">{check.detail}</span> : null}
        </li>
      ))}
    </ul>
  )
}

function DocumentPreview({ entry }: { entry: JournalEntryDetail }) {
  const doc = entry.document
  if (!doc) return null
  const url = documentUrl(doc.document_id)
  return (
    <Section title="Document">
      {doc.mime === 'application/pdf' ? (
        <iframe title="Invoice document" src={url} className="h-[480px] w-full border" />
      ) : (
        <img alt="Invoice document" src={url} className="w-full border" />
      )}
      <a
        href={url}
        target="_blank"
        rel="noreferrer"
        className="inline-flex items-center gap-1 text-sm underline-offset-2 hover:underline"
      >
        Open in new tab
        <ArrowSquareOutIcon aria-hidden className="size-4" />
      </a>
    </Section>
  )
}

function Reversal({ entry }: { entry: JournalEntryDetail }) {
  const range = useRange()
  const linked = entry.reversed_by ?? entry.reverses
  if (!linked) return null
  const label = entry.reversed_by ? 'Reversed by' : 'Reverses'
  return (
    <Section title="Reversal">
      <Link
        to="/accounting/journal/$entryNo"
        params={{ entryNo: linked.entry_no }}
        search={range}
        className="inline-flex items-center gap-1 text-sm underline-offset-2 hover:underline"
      >
        <ArrowsCounterClockwiseIcon aria-hidden className="size-4" />
        {label} {linked.entry_no}
      </Link>
    </Section>
  )
}

function Audit({ entry }: { entry: JournalEntryDetail }) {
  return (
    <ul className="flex flex-col gap-1 text-sm">
      {entry.audit.map((row) => (
        <li key={`${row.at}-${row.action}`} className="flex flex-wrap gap-2">
          <span className="text-muted-foreground">{formatTimestamp(row.at)}</span>
          <span>{ACTORS[row.actor] ?? row.actor}</span>
          <span>{row.action}</span>
        </li>
      ))}
    </ul>
  )
}

export function EntrySheet({ entryNo }: { entryNo: string }) {
  const navigate = useNavigate()
  const range = useRange()
  const query = useEntry(entryNo)
  const entry = query.data
  const notFound = query.error instanceof ApiError && query.error.status === 404

  return (
    <Sheet
      open
      onOpenChange={(open) => {
        if (!open) void navigate({ to: '/accounting/journal', search: range })
      }}
    >
      <SheetContent className="overflow-y-auto">
        <SheetHeader>
          <SheetTitle>{entryNo}</SheetTitle>
          <SheetDescription>
            {entry ? `${formatDate(entry.date)}, ${entry.description}` : ' '}
          </SheetDescription>
          {entry ? (
            <div className="flex gap-2">
              <SourceBadge source={entry.source} kind={entry.kind} />
              <StatusBadge status={entry.status} />
            </div>
          ) : null}
        </SheetHeader>
        <div className="flex flex-col gap-4 px-4 pb-6">
          {query.isPending ? <LoadingState rows={6} /> : null}
          {notFound ? <p className="text-sm">Entry not found.</p> : null}
          {query.isError && !notFound ? (
            <ErrorState
              message={`Could not load entry ${entryNo}.`}
              onRetry={() => void query.refetch()}
            />
          ) : null}
          {entry ? (
            <>
              {entry.note ? <p className="text-sm text-muted-foreground">{entry.note}</p> : null}
              <Section title="Lines">
                <Lines entry={entry} />
              </Section>
              <Section title="Checks">
                <Checks entry={entry} />
              </Section>
              <DocumentPreview entry={entry} />
              <Reversal entry={entry} />
              <Section title="Audit trail">
                <Audit entry={entry} />
              </Section>
            </>
          ) : null}
        </div>
      </SheetContent>
    </Sheet>
  )
}
