import { useQueryClient } from '@tanstack/react-query'
import { type FormEvent, useEffect, useMemo, useState } from 'react'
import { toast } from 'sonner'
import { FormField } from '@/components/form-field'
import { ErrorState, Spinner, TableLoadingRows } from '@/components/states'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { useAccounts } from '@/features/accounts/api'
import { ApiError } from '@/lib/api'
import { formatDate, formatMoney } from '@/lib/format'
import { centsToText, type OpeningLine, parseCents, saveOpening, useOpening } from './api'

type Amounts = Record<number, { debit: string; credit: string }>

function serverMessage(error: unknown): string {
  if (error instanceof ApiError && error.status === 422) {
    return 'The opening balances were not saved. Check the amounts and try again.'
  }
  return 'The opening balances were not saved. Try again.'
}

function blank(value: string): string {
  return parseCents(value) === 0n ? '' : formatMoney(value).replace(/,/g, '')
}

// See planning/02-design.md#settings (F-004)
export function OpeningBalancesPage() {
  const queryClient = useQueryClient()
  const accounts = useAccounts()
  const opening = useOpening()
  const [asAt, setAsAt] = useState('')
  const [amounts, setAmounts] = useState<Amounts>({})
  const [confirming, setConfirming] = useState(false)
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  useEffect(() => {
    if (!opening.data) return
    setAsAt(opening.data.as_at ?? '')
    const next: Amounts = {}
    for (const line of opening.data.lines) {
      next[line.account_id] = { debit: blank(line.debit), credit: blank(line.credit) }
    }
    setAmounts(next)
  }, [opening.data])

  const inOpening = new Set(opening.data?.lines.map((line) => line.account_id) ?? [])
  const rows = (accounts.data ?? []).filter(
    (account) => account.active || inOpening.has(account.id),
  )

  const totals = useMemo(() => {
    let debit = 0n
    let credit = 0n
    let invalid = false
    for (const value of Object.values(amounts)) {
      const d = parseCents(value.debit)
      const c = parseCents(value.credit)
      if (d === null || c === null) {
        invalid = true
        continue
      }
      debit += d
      credit += c
    }
    return { debit, credit, difference: debit - credit, invalid }
  }, [amounts])

  const balanced = totals.difference === 0n
  const canSave =
    !saving &&
    !totals.invalid &&
    balanced &&
    totals.debit > 0n &&
    asAt !== '' &&
    !accounts.isPending

  function setAmount(id: number, side: 'debit' | 'credit', value: string) {
    setAmounts((prev) => ({
      ...prev,
      [id]: { debit: prev[id]?.debit ?? '', credit: prev[id]?.credit ?? '', [side]: value },
    }))
  }

  function lines(): OpeningLine[] {
    const out: OpeningLine[] = []
    for (const [id, value] of Object.entries(amounts)) {
      const debit = parseCents(value.debit) ?? 0n
      const credit = parseCents(value.credit) ?? 0n
      if (debit === 0n && credit === 0n) continue
      out.push({
        account_id: Number(id),
        debit: centsToText(debit),
        credit: centsToText(credit),
      })
    }
    return out
  }

  async function save() {
    setSaving(true)
    setFormError(null)
    try {
      const saved = await saveOpening(queryClient, { as_at: asAt, lines: lines() })
      toast.success(`Opening entry ${saved.entry_no} posted`)
      setConfirming(false)
    } catch (error) {
      setFormError(serverMessage(error))
      setConfirming(false)
    } finally {
      setSaving(false)
    }
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault()
    if (!canSave) return
    if (opening.data?.entry_no) {
      setConfirming(true)
      return
    }
    void save()
  }

  if (accounts.isError || opening.isError) {
    return (
      <ErrorState
        message="Could not load opening balances."
        onRetry={() => {
          void accounts.refetch()
          void opening.refetch()
        }}
      />
    )
  }

  return (
    <section className="flex flex-col gap-4">
      <h2 className="text-lg font-semibold">Opening balances</h2>
      {opening.data?.entry_no && opening.data.as_at ? (
        <p className="text-sm text-muted-foreground">
          Current opening entry {opening.data.entry_no} as at {formatDate(opening.data.as_at)}.
        </p>
      ) : (
        <p className="text-sm text-muted-foreground">
          Enter the balance of each account on the day your books start.
        </p>
      )}
      <form noValidate onSubmit={onSubmit} className="flex flex-col gap-4">
        <FormField id="opening-as-at" label="As at">
          {(a11y) => (
            <Input
              {...a11y}
              type="date"
              className="w-[180px]"
              value={asAt}
              onChange={(event) => setAsAt(event.target.value)}
            />
          )}
        </FormField>
        <div className="overflow-x-auto">
          <Table className="min-w-[480px]">
            <TableHeader>
              <TableRow className="hover:bg-muted">
                <TableHead>Account</TableHead>
                <TableHead className="w-[140px] text-right">Debit</TableHead>
                <TableHead className="w-[140px] text-right">Credit</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {accounts.isPending || opening.isPending ? <TableLoadingRows columns={3} /> : null}
              {rows.map((account) => {
                const value = amounts[account.id] ?? { debit: '', credit: '' }
                const label = `${account.code} ${account.name}`
                return (
                  <TableRow key={account.id}>
                    <TableCell>
                      <span className="tabular-nums">{account.code}</span> {account.name}
                    </TableCell>
                    <TableCell>
                      <Input
                        aria-label={`Debit for ${label}`}
                        inputMode="decimal"
                        className="text-right tabular-nums"
                        aria-invalid={parseCents(value.debit) === null || undefined}
                        value={value.debit}
                        onChange={(event) => setAmount(account.id, 'debit', event.target.value)}
                      />
                    </TableCell>
                    <TableCell>
                      <Input
                        aria-label={`Credit for ${label}`}
                        inputMode="decimal"
                        className="text-right tabular-nums"
                        aria-invalid={parseCents(value.credit) === null || undefined}
                        value={value.credit}
                        onChange={(event) => setAmount(account.id, 'credit', event.target.value)}
                      />
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
            <tfoot className="border-t">
              <TableRow className="hover:bg-muted">
                <TableCell className="font-semibold">Total</TableCell>
                <TableCell className="text-right font-semibold tabular-nums">
                  {formatMoney(centsToText(totals.debit))}
                </TableCell>
                <TableCell className="text-right font-semibold tabular-nums">
                  {formatMoney(centsToText(totals.credit))}
                </TableCell>
              </TableRow>
              <TableRow className="hover:bg-muted">
                <TableCell>Difference</TableCell>
                <TableCell
                  colSpan={2}
                  data-testid="opening-difference"
                  className={`text-right tabular-nums ${balanced ? '' : 'text-destructive'}`}
                >
                  {formatMoney(
                    centsToText(totals.difference < 0n ? -totals.difference : totals.difference),
                  )}
                </TableCell>
              </TableRow>
            </tfoot>
          </Table>
        </div>
        {!balanced ? <p className="text-sm text-destructive">Debits must equal credits.</p> : null}
        {totals.invalid ? (
          <p className="text-sm text-destructive">Use amounts with up to 2 decimal places.</p>
        ) : null}
        {formError ? (
          <p role="alert" className="text-sm text-destructive">
            {formError}
          </p>
        ) : null}
        <div>
          <Button type="submit" disabled={!canSave}>
            {saving && !confirming ? <Spinner /> : null}
            Save
          </Button>
        </div>
      </form>
      <Dialog open={confirming} onOpenChange={(open) => !saving && setConfirming(open)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Replace opening entry</DialogTitle>
            <DialogDescription>
              This reverses {opening.data?.entry_no} and posts a new opening entry.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <DialogClose asChild>
              <Button type="button" variant="secondary" disabled={saving}>
                Cancel
              </Button>
            </DialogClose>
            <Button type="button" disabled={saving} onClick={() => void save()}>
              {saving ? <Spinner /> : null}
              Reverse and post
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </section>
  )
}
