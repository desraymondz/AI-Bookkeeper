import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

// See planning/02-design.md#settings (Telegram, Suppliers)
export function CopyLink({
  value,
  inputLabel,
  buttonLabel,
  toastMessage,
}: {
  value: string
  inputLabel: string
  buttonLabel: string
  toastMessage?: string
}) {
  async function copy() {
    try {
      await navigator.clipboard.writeText(value)
      toast.success(toastMessage ?? 'Link copied')
    } catch {
      toast.error('Could not copy. Select the link and copy it.')
    }
  }

  return (
    <div className="flex items-center gap-2">
      <Input
        readOnly
        aria-label={inputLabel}
        value={value}
        onFocus={(event) => event.currentTarget.select()}
      />
      <Button type="button" variant="secondary" onClick={() => void copy()}>
        {buttonLabel}
      </Button>
    </div>
  )
}
