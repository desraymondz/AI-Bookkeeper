import { TelegramLogoIcon } from '@phosphor-icons/react'
import { useQueryClient } from '@tanstack/react-query'
import { QRCodeSVG } from 'qrcode.react'
import { useEffect, useRef, useState } from 'react'
import { toast } from 'sonner'
import { ErrorState, LoadingState, Spinner } from '@/components/states'
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
import { createBossLink, type InviteLink, invalidateBossLink, useBossLink } from './api'
import { CopyLink } from './copy-link'
import { formatDateTime, useBusinessTimezone } from './format'

const POLL_MS = 5000

// See planning/02-design.md#settings (Telegram)
export function TelegramPage() {
  const queryClient = useQueryClient()
  const timezone = useBusinessTimezone()
  const [link, setLink] = useState<InviteLink | null>(null)
  const [creating, setCreating] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const baseline = useRef<string | null>(null)
  const { data, isPending, isError, refetch } = useBossLink(link ? POLL_MS : false)

  useEffect(() => {
    if (!link || !data?.connected) return
    if (data.linked_at === baseline.current) return
    setLink(null)
    toast.success('Telegram connected')
  }, [link, data])

  async function generate() {
    setCreating(true)
    try {
      baseline.current = data?.linked_at ?? null
      setLink(await createBossLink())
      setConfirming(false)
      await invalidateBossLink(queryClient)
    } catch {
      toast.error('The link was not created. Try again.')
    } finally {
      setCreating(false)
    }
  }

  if (isError) {
    return (
      <ErrorState
        message="Could not load the Telegram connection."
        onRetry={() => void refetch()}
      />
    )
  }
  if (isPending) return <LoadingState rows={2} />

  const connected = data.connected
  const who = data.username ? `@${data.username}` : (data.display_name ?? 'Telegram')

  return (
    <section className="flex flex-col gap-4">
      <h2 className="text-lg font-semibold">Telegram</h2>
      <div className="flex items-center gap-3">
        <Badge variant={connected ? 'filled' : 'muted'}>
          {connected ? `Connected as ${who}` : 'Not connected'}
        </Badge>
      </div>
      <div>
        {connected ? (
          <Button variant="secondary" onClick={() => setConfirming(true)}>
            Reconnect
          </Button>
        ) : (
          <Button onClick={() => void generate()} disabled={creating}>
            {creating ? <Spinner /> : null}
            Connect Telegram
          </Button>
        )}
      </div>
      {link ? (
        <div className="flex flex-col gap-3">
          <p className="text-sm text-muted-foreground">
            Open the link in Telegram and press Start. This link works once.
          </p>
          <CopyLink
            value={link.url}
            inputLabel="Telegram link"
            buttonLabel="Copy"
            toastMessage="Link copied"
          />
          <div>
            <Button asChild>
              <a href={link.url} target="_blank" rel="noopener noreferrer">
                <TelegramLogoIcon aria-hidden />
                Open in Telegram
              </a>
            </Button>
          </div>
          <div role="img" aria-label="QR code" className="w-fit bg-white p-4">
            <QRCodeSVG value={link.url} size={168} bgColor="#ffffff" fgColor="#000000" />
          </div>
          <p className="text-sm text-muted-foreground">
            Expires {formatDateTime(link.expires_at, timezone)}
          </p>
        </div>
      ) : null}
      <Dialog open={confirming} onOpenChange={setConfirming}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Reconnect Telegram</DialogTitle>
            <DialogDescription>
              Your current Telegram account will be disconnected.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <DialogClose asChild>
              <Button type="button" variant="secondary">
                Cancel
              </Button>
            </DialogClose>
            <Button onClick={() => void generate()} disabled={creating}>
              {creating ? <Spinner /> : null}
              Create new link
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </section>
  )
}
