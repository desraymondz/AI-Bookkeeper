import { TelegramLogoIcon } from '@phosphor-icons/react'
import { Button } from '@/components/ui/button'
import { telegramBotUrl, useAppConfig } from '@/features/config/api'
import { cn } from '@/lib/utils'

// See planning/01-prd.md#F-029 and planning/02-design.md#settings
export function OpenTelegramButton({ className }: { className?: string }) {
  const { data } = useAppConfig()
  const botUsername = data?.bot_username
  if (!botUsername) return null

  return (
    <Button asChild variant="secondary" className={cn(className)}>
      <a href={telegramBotUrl(botUsername)} target="_blank" rel="noopener noreferrer">
        <TelegramLogoIcon aria-hidden />
        Open in Telegram
      </a>
    </Button>
  )
}
