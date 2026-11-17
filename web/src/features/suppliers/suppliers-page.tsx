import { DotsThreeIcon, PlusIcon } from '@phosphor-icons/react'
import { useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { toast } from 'sonner'
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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { type Supplier, updateSupplier, useSuppliers } from './api'
import { InviteDialog } from './invite-dialog'
import { SupplierDialog } from './supplier-dialog'

function RowMenu({
  supplier,
  onEdit,
  onInvite,
  onDeactivate,
}: {
  supplier: Supplier
  onEdit: () => void
  onInvite: () => void
  onDeactivate: () => void
}) {
  const queryClient = useQueryClient()

  async function reactivate() {
    try {
      await updateSupplier(queryClient, supplier.id, { active: true })
    } catch {
      toast.error('The supplier was not changed. Try again.')
    }
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" aria-label={`Actions for ${supplier.name}`}>
          <DotsThreeIcon aria-hidden weight="bold" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem onSelect={onEdit}>Edit</DropdownMenuItem>
        {supplier.active ? (
          <>
            <DropdownMenuItem onSelect={onInvite}>Create invite</DropdownMenuItem>
            <DropdownMenuItem onSelect={onDeactivate}>Deactivate</DropdownMenuItem>
          </>
        ) : (
          <DropdownMenuItem onSelect={() => void reactivate()}>Reactivate</DropdownMenuItem>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

function DeactivateDialog({
  supplier,
  onClose,
}: {
  supplier: Supplier | null
  onClose: () => void
}) {
  const queryClient = useQueryClient()
  const [saving, setSaving] = useState(false)

  async function confirm() {
    if (!supplier) return
    setSaving(true)
    try {
      await updateSupplier(queryClient, supplier.id, { active: false })
      toast.success('Supplier deactivated')
      onClose()
    } catch {
      toast.error('The supplier was not changed. Try again.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open={supplier !== null} onOpenChange={(open) => (open ? undefined : onClose())}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Deactivate {supplier?.name}</DialogTitle>
          <DialogDescription>
            Later messages from this supplier are treated like a stranger's. Existing entries stay.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <DialogClose asChild>
            <Button type="button" variant="secondary">
              Cancel
            </Button>
          </DialogClose>
          <Button variant="destructive" onClick={() => void confirm()} disabled={saving}>
            Deactivate
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// See planning/02-design.md#settings (Suppliers)
export function SuppliersPage() {
  const { data, isPending, isError, refetch } = useSuppliers()
  const [editor, setEditor] = useState<{ supplier: Supplier | null } | null>(null)
  const [inviting, setInviting] = useState<Supplier | null>(null)
  const [deactivating, setDeactivating] = useState<Supplier | null>(null)

  return (
    <section className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-lg font-semibold">Suppliers</h2>
        <Button onClick={() => setEditor({ supplier: null })}>
          <PlusIcon aria-hidden />
          Add supplier
        </Button>
      </div>
      {isError ? (
        <ErrorState message="Could not load suppliers." onRetry={() => void refetch()} />
      ) : (
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-muted">
              <TableHead>Name</TableHead>
              <TableHead>UEN</TableHead>
              <TableHead>Default account</TableHead>
              <TableHead>Terms (days)</TableHead>
              <TableHead>Telegram</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="w-10">
                <span className="sr-only">Actions</span>
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isPending ? <TableLoadingRows columns={7} /> : null}
            {(data ?? []).map((supplier) => (
              <TableRow key={supplier.id}>
                <TableCell>{supplier.name}</TableCell>
                <TableCell>{supplier.uen ?? ''}</TableCell>
                <TableCell>{supplier.default_account_name}</TableCell>
                <TableCell className="tabular-nums">{supplier.terms_days}</TableCell>
                <TableCell>{supplier.telegram_username_hint ?? ''}</TableCell>
                <TableCell>
                  <Badge variant={supplier.active ? 'filled' : 'muted'}>
                    {supplier.active ? 'Active' : 'Inactive'}
                  </Badge>
                </TableCell>
                <TableCell>
                  <RowMenu
                    supplier={supplier}
                    onEdit={() => setEditor({ supplier })}
                    onInvite={() => setInviting(supplier)}
                    onDeactivate={() => setDeactivating(supplier)}
                  />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
      {data?.length === 0 ? <EmptyState message="No suppliers yet." /> : null}
      <SupplierDialog
        supplier={editor?.supplier ?? null}
        open={editor !== null}
        onOpenChange={(open) => (open ? undefined : setEditor(null))}
      />
      <InviteDialog supplier={inviting} onClose={() => setInviting(null)} />
      <DeactivateDialog supplier={deactivating} onClose={() => setDeactivating(null)} />
    </section>
  )
}
