import type { SettingsData, SettingsPayload } from './api'

// See api/src/bookkeeper/settings_service.py and planning/01-prd.md#F-002
export type FormValues = {
  name: string
  currency: string
  timezone: string
  fy_start_month: string
  gst_registered: boolean
  gst_rate: string
  price_rule: string
  dup_window_days: string
  reminder_days: string
  recap_time: string
  report_day: string
  report_time: string
}

export type FieldErrors = Partial<Record<keyof FormValues, string>>

const HHMM = /^([01]\d|2[0-3]):([0-5]\d)$/
const TIME_MESSAGE = 'Use HH:MM, for example 21:00.'
const GST_MESSAGE = 'GST rate must be a number from 0 to 100.'

export function formatRate(rate: string | number) {
  const text = String(rate)
  return text.includes('.') ? text.replace(/0+$/, '').replace(/\.$/, '') : text
}

export function toFormValues(data: SettingsData): FormValues {
  return {
    name: data.name,
    currency: data.currency,
    timezone: data.timezone,
    fy_start_month: String(data.fy_start_month),
    gst_registered: data.gst_registered,
    gst_rate: formatRate(data.gst_rate),
    price_rule: data.price_rule,
    dup_window_days: String(data.dup_window_days),
    reminder_days: String(data.reminder_days),
    recap_time: data.recap_time,
    report_day: String(data.report_day),
    report_time: data.report_time,
  }
}

function intInRange(value: string, min: number, max: number) {
  if (!/^\d+$/.test(value.trim())) return false
  const parsed = Number(value)
  return parsed >= min && parsed <= max
}

export function validate(values: FormValues): FieldErrors {
  const errors: FieldErrors = {}
  if (!values.name.trim()) errors.name = 'Enter the business name.'
  if (!/^[A-Za-z]{3}$/.test(values.currency.trim())) {
    errors.currency = 'Use a 3-letter currency code, for example SGD.'
  }
  if (!values.timezone.trim())
    errors.timezone = 'Enter an IANA timezone, for example Asia/Singapore.'
  const rate = values.gst_rate.trim()
  if (!/^\d{1,3}(\.\d{1,2})?$/.test(rate) || Number(rate) > 100) errors.gst_rate = GST_MESSAGE
  if (!intInRange(values.dup_window_days, 0, 3650)) {
    errors.dup_window_days = 'Enter a whole number of days from 0 to 3650.'
  }
  if (!intInRange(values.reminder_days, 0, 365)) {
    errors.reminder_days = 'Enter a whole number of days from 0 to 365.'
  }
  if (!HHMM.test(values.recap_time.trim())) errors.recap_time = TIME_MESSAGE
  if (!intInRange(values.report_day, 1, 28)) errors.report_day = 'Enter a day from 1 to 28.'
  if (!HHMM.test(values.report_time.trim())) errors.report_time = TIME_MESSAGE
  return errors
}

export function toPayload(values: FormValues): SettingsPayload {
  return {
    name: values.name.trim(),
    currency: values.currency.trim().toUpperCase(),
    timezone: values.timezone.trim(),
    fy_start_month: Number(values.fy_start_month),
    gst_registered: values.gst_registered,
    gst_rate: values.gst_rate.trim(),
    price_rule: values.price_rule,
    dup_window_days: Number(values.dup_window_days),
    reminder_days: Number(values.reminder_days),
    recap_time: values.recap_time.trim(),
    report_day: Number(values.report_day),
    report_time: values.report_time.trim(),
  }
}

export function serverErrors(body: unknown): FieldErrors {
  const errors: FieldErrors = {}
  const detail = body && typeof body === 'object' && 'detail' in body ? body.detail : null
  if (!Array.isArray(detail)) return errors
  for (const item of detail) {
    if (!item || typeof item !== 'object' || !('loc' in item) || !Array.isArray(item.loc)) continue
    const field = item.loc[item.loc.length - 1]
    const message = 'msg' in item && typeof item.msg === 'string' ? item.msg : 'Invalid value.'
    if (typeof field === 'string') errors[field as keyof FormValues] = message
  }
  return errors
}
