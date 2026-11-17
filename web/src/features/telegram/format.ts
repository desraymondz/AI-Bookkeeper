import { useSettings } from '@/features/settings/api'

// See planning/02-design.md#settings (Suppliers, Telegram)
export function useBusinessTimezone() {
  const { data } = useSettings()
  return data?.settings?.timezone
}

export function formatDateTime(value: string, timeZone?: string) {
  return new Intl.DateTimeFormat('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
    timeZone,
  }).format(new Date(value))
}

export function formatDate(value: string, timeZone?: string) {
  return new Intl.DateTimeFormat('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    timeZone,
  }).format(new Date(value))
}
