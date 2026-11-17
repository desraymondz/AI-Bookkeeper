import { useEffect, useState } from 'react'
import { ErrorState, Spinner } from '@/components/states'
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
import { createSupplierLink, type InviteLink } from '@/features/telegram/api'
import { CopyLink } from '@/features/telegram/copy-link'
import { formatDateTime, useBusinessTimezone } from '@/features/telegram/format'
import type { Supplier } from './api'

// See planning/01-prd.md#F-007 (F-007.2) and planning/02-design.md#settings (Suppliers)
export function InviteDialog({
  supplier,
  onClose,
}: {
  supplier: Supplier | null
  onClose: () => void
}) {
  const timezone = useBusinessTimezone()
  const [link, setLink] = useState<InviteLink | null>(null)
  const [failed, setFailed] = useState(false)
  const supplierId = supplier?.id

  useEffect(() => {
    if (supplierId === undefined) return
    let current = true
    setLink(null)
    setFailed(false)
    createSupplierLink(supplierId)
      .then((created) => {
        if (current) setLink(created)
      })
      .catch(() => {
        if (current) setFailed(true)
      })
    return () => {
      current = false
    }
  }, [supplierId])

  return (
    <Dialog open={supplier !== null} onOpenChange={(open) => (open ? undefined : onClose())}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Invite link for {supplier?.name}</DialogTitle>
          <DialogDescription>
            Send this link to the supplier. They open it in Telegram and press Start.
          </DialogDescription>
        </DialogHeader>
        {failed ? <ErrorState message="The invite was not created. Try again." /> : null}
        {!link && !failed ? (
          <div role="status" className="flex items-center gap-2 text-sm text-muted-foreground">
            <Spinner />
            Creating link
          </div>
        ) : null}
        {link ? (
          <div className="flex flex-col gap-3">
            <CopyLink
              value={link.url}
              inputLabel="Invite link"
              buttonLabel="Copy link"
              toastMessage="Link copied"
            />
            <p className="text-sm">Expires {formatDateTime(link.expires_at, timezone)}</p>
            <p className="text-sm text-muted-foreground">
              This link can be used once. Create a new invite if it is lost.
            </p>
          </div>
        ) : null}
        <DialogFooter>
          <DialogClose asChild>
            <Button type="button" variant="secondary">
              Close
            </Button>
          </DialogClose>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
