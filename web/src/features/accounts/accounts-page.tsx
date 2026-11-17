import { DotsThreeIcon, PlusIcon } from '@phosphor-icons/react'
import { useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { toast } from 'sonner'
import { ErrorState, TableLoadingRows } from '@/components/states'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { AddAccountDialog } from './add-account-dialog'
import { type Account, setAccountActive, typeLabel, useAccounts } from './api'

function RowMenu({ account }: { account: Account }) {
  const queryClient = useQueryClient()
  const label = `Actions for ${account.code} ${account.name}`
  const locked = account.has_postings

  async function toggle() {
    try {
      await setAccountActive(queryClient, account.id, !account.active)
    } catch {
      toast.error('The account was not changed. Try again.')
    }
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" aria-label={label}>
          <DotsThreeIcon aria-hidden weight="bold" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {account.active ? (
          locked ? (
            <Tooltip>
              <TooltipTrigger asChild>
                <div>
                  <DropdownMenuItem disabled aria-disabled="true">
                    Deactivate
                  </DropdownMenuItem>
                </div>
              </TooltipTrigger>
              <TooltipContent>Has postings</TooltipContent>
            </Tooltip>
          ) : (
            <DropdownMenuItem onSelect={() => void toggle()}>Deactivate</DropdownMenuItem>
          )
        ) : (
          <DropdownMenuItem onSelect={() => void toggle()}>Reactivate</DropdownMenuItem>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

// See planning/02-design.md#settings (Chart of accounts)
export function AccountsPage() {
  const { data, isPending, isError, refetch } = useAccounts()
  const [showInactive, setShowInactive] = useState(false)
  const [adding, setAdding] = useState(false)
  const visible = (data ?? []).filter((account) => showInactive || account.active)

  return (
    <section className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-lg font-semibold">Chart of accounts</h2>
        <Button onClick={() => setAdding(true)}>
          <PlusIcon aria-hidden />
          Add account
        </Button>
      </div>
      <div className="flex items-center gap-3">
        <Switch id="show-inactive" checked={showInactive} onCheckedChange={setShowInactive} />
        <Label htmlFor="show-inactive">Show inactive</Label>
      </div>
      {isError ? (
        <ErrorState message="Could not load accounts." onRetry={() => void refetch()} />
      ) : (
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-muted">
              <TableHead>Code</TableHead>
              <TableHead>Name</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Postings</TableHead>
              <TableHead className="w-10">
                <span className="sr-only">Actions</span>
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isPending ? <TableLoadingRows columns={6} /> : null}
            {visible.map((account) => (
              <TableRow key={account.id}>
                <TableCell className="tabular-nums">{account.code}</TableCell>
                <TableCell>{account.name}</TableCell>
                <TableCell>
                  <Badge variant="outline">{typeLabel(account.type)}</Badge>
                </TableCell>
                <TableCell>
                  <Badge variant={account.active ? 'filled' : 'muted'}>
                    {account.active ? 'Active' : 'Inactive'}
                  </Badge>
                </TableCell>
                <TableCell>{account.has_postings ? 'Yes' : 'No'}</TableCell>
                <TableCell>
                  <RowMenu account={account} />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
      <AddAccountDialog open={adding} onOpenChange={setAdding} />
    </section>
  )
}
