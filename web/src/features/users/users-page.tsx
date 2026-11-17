import { DotsThreeIcon } from '@phosphor-icons/react'
import { useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { toast } from 'sonner'
import { FormField } from '@/components/form-field'
import { EmptyState, ErrorState, TableLoadingRows } from '@/components/states'
import { Badge } from '@/components/ui/badge'
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
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Select } from '@/components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { useSuppliers } from '@/features/suppliers/api'
import { formatDate, useBusinessTimezone } from '@/features/telegram/format'
import { type AppUser, revokeUser, updateUser, useUsers } from './api'

const STATUS_LABEL = { active: 'Active', deactivated: 'Deactivated', blocked: 'Blocked' } as const

function userName(user: AppUser) {
  return user.display_name ?? (user.username ? `@${user.username}` : `User ${user.id}`)
}

type Pending = { kind: 'supplier' | 'deactivate' | 'revoke'; user: AppUser } | null

function RowMenu({
  user,
  onPick,
}: {
  user: AppUser
  onPick: (kind: NonNullable<Pending>['kind']) => void
}) {
  const queryClient = useQueryClient()

  async function reactivate() {
    try {
      await updateUser(queryClient, user.id, { status: 'active' })
    } catch {
      toast.error('The user was not changed. Try again.')
    }
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" aria-label={`Actions for ${userName(user)}`}>
          <DotsThreeIcon aria-hidden weight="bold" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {user.role === 'boss' ? (
          <DropdownMenuItem disabled aria-disabled="true">
            The boss cannot be changed
          </DropdownMenuItem>
        ) : (
          <>
            <DropdownMenuItem onSelect={() => onPick('supplier')}>
              Change linked supplier
            </DropdownMenuItem>
            {user.status === 'active' ? (
              <DropdownMenuItem onSelect={() => onPick('deactivate')}>Deactivate</DropdownMenuItem>
            ) : (
              <DropdownMenuItem onSelect={() => void reactivate()}>Reactivate</DropdownMenuItem>
            )}
            <DropdownMenuItem className="text-destructive" onSelect={() => onPick('revoke')}>
              Revoke link
            </DropdownMenuItem>
          </>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

function SupplierPicker({ user, onClose }: { user: AppUser | null; onClose: () => void }) {
  const queryClient = useQueryClient()
  const suppliers = useSuppliers()
  const [choice, setChoice] = useState<{ userId: number; value: string } | null>(null)
  const [saving, setSaving] = useState(false)
  const active = (suppliers.data ?? []).filter((supplier) => supplier.active)
  const value =
    choice && choice.userId === user?.id ? choice.value : String(user?.supplier_id ?? '')

  async function save() {
    if (!user || !value) return
    setSaving(true)
    try {
      await updateUser(queryClient, user.id, { supplier_id: Number(value) })
      toast.success('Linked supplier changed')
      onClose()
    } catch {
      toast.error('The linked supplier was not changed. Try again.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open={user !== null} onOpenChange={(open) => (open ? undefined : onClose())}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Change linked supplier</DialogTitle>
          <DialogDescription>
            Their next invoice is checked against the supplier you pick.
          </DialogDescription>
        </DialogHeader>
        <FormField id="user-supplier" label="Supplier">
          {(a11y) => (
            <Select
              {...a11y}
              value={value}
              onChange={(event) => setChoice({ userId: user?.id ?? 0, value: event.target.value })}
            >
              {active.map((supplier) => (
                <option key={supplier.id} value={supplier.id}>
                  {supplier.name}
                </option>
              ))}
            </Select>
          )}
        </FormField>
        <DialogFooter>
          <DialogClose asChild>
            <Button type="button" variant="secondary">
              Cancel
            </Button>
          </DialogClose>
          <Button onClick={() => void save()} disabled={saving || !value}>
            Save
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function ConfirmDialog({
  pending,
  onClose,
}: {
  pending: NonNullable<Pending> | null
  onClose: () => void
}) {
  const queryClient = useQueryClient()
  const [saving, setSaving] = useState(false)
  const revoke = pending?.kind === 'revoke'

  async function confirm() {
    if (!pending) return
    setSaving(true)
    try {
      if (revoke) await revokeUser(queryClient, pending.user.id)
      else await updateUser(queryClient, pending.user.id, { status: 'deactivated' })
      toast.success(revoke ? 'Link revoked' : 'User deactivated')
      onClose()
    } catch {
      toast.error('The user was not changed. Try again.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open={pending !== null} onOpenChange={(open) => (open ? undefined : onClose())}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            {revoke ? 'Revoke link' : 'Deactivate user'}
            {pending ? ` for ${userName(pending.user)}` : ''}
          </DialogTitle>
          <DialogDescription>
            Their next message gets the stranger reply. Existing entries stay.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <DialogClose asChild>
            <Button type="button" variant="secondary">
              Cancel
            </Button>
          </DialogClose>
          <Button variant="destructive" onClick={() => void confirm()} disabled={saving}>
            {revoke ? 'Revoke link' : 'Deactivate'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// See planning/02-design.md#settings (Users and roles)
export function UsersPage() {
  const { data, isPending, isError, refetch } = useUsers()
  const timezone = useBusinessTimezone()
  const [pending, setPending] = useState<Pending>(null)
  const [picking, setPicking] = useState<AppUser | null>(null)

  function pick(user: AppUser, kind: NonNullable<Pending>['kind']) {
    if (kind === 'supplier') setPicking(user)
    else setPending({ kind, user })
  }

  return (
    <section className="flex flex-col gap-4">
      <h2 className="text-lg font-semibold">Users and roles</h2>
      {isError ? (
        <ErrorState message="Could not load users." onRetry={() => void refetch()} />
      ) : (
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-muted">
              <TableHead>Display name</TableHead>
              <TableHead>Username</TableHead>
              <TableHead>Role</TableHead>
              <TableHead>Linked supplier</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Linked</TableHead>
              <TableHead className="w-10">
                <span className="sr-only">Actions</span>
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isPending ? <TableLoadingRows columns={7} /> : null}
            {(data ?? []).map((user) => (
              <TableRow key={user.id}>
                <TableCell>{user.display_name ?? ''}</TableCell>
                <TableCell>{user.username ? `@${user.username}` : ''}</TableCell>
                <TableCell>
                  <Badge variant={user.role === 'boss' ? 'filled' : 'outline'}>
                    {user.role === 'boss' ? 'Boss' : 'Supplier'}
                  </Badge>
                </TableCell>
                <TableCell>{user.supplier_name ?? ''}</TableCell>
                <TableCell>
                  <Badge variant={user.status === 'active' ? 'filled' : 'muted'}>
                    {STATUS_LABEL[user.status]}
                  </Badge>
                </TableCell>
                <TableCell>{user.linked_at ? formatDate(user.linked_at, timezone) : ''}</TableCell>
                <TableCell>
                  <RowMenu user={user} onPick={(kind) => pick(user, kind)} />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
      {data && !data.some((user) => user.role === 'supplier') ? (
        <EmptyState message="No one has linked Telegram yet." />
      ) : null}
      <p className="text-sm text-muted-foreground">There is exactly one boss.</p>
      <SupplierPicker user={picking} onClose={() => setPicking(null)} />
      <ConfirmDialog pending={pending} onClose={() => setPending(null)} />
    </section>
  )
}
