import { createFileRoute } from '@tanstack/react-router'
import { TelegramPage } from '@/features/telegram/telegram-page'

// See planning/02-design.md#settings (F-006)
export const Route = createFileRoute('/_app/settings/telegram')({
  component: TelegramPage,
})
