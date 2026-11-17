import { useQueryClient } from '@tanstack/react-query'
import { type FormEvent, type ReactNode, useState } from 'react'
import { FormField } from '@/components/form-field'
import { Spinner } from '@/components/states'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { ApiError } from '@/lib/api'
import { type SettingsData, saveSettings } from './api'
import {
  type FieldErrors,
  type FormValues,
  serverErrors,
  toFormValues,
  toPayload,
  validate,
} from './validation'

const MONTHS = [
  'January',
  'February',
  'March',
  'April',
  'May',
  'June',
  'July',
  'August',
  'September',
  'October',
  'November',
  'December',
]

const PRICE_RULES = [
  { value: 'any_change', label: 'Any unit price change' },
  { value: 'increase_only', label: 'Unit price increase only' },
] as const

type SettingsFormProps = {
  initial: SettingsData
  submitLabel: string
  onSaved: (saved: SettingsData) => void | Promise<void>
  footer?: ReactNode
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <fieldset className="flex flex-col gap-4">
      <legend className="mb-1 text-lg font-semibold">{title}</legend>
      {children}
    </fieldset>
  )
}

// See planning/02-design.md#first-run-setup-f-0021-to-f-0023
export function SettingsForm({ initial, submitLabel, onSaved, footer }: SettingsFormProps) {
  const queryClient = useQueryClient()
  const [values, setValues] = useState<FormValues>(() => toFormValues(initial))
  const [errors, setErrors] = useState<FieldErrors>({})
  const [formError, setFormError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  const set = <K extends keyof FormValues>(key: K, value: FormValues[K]) =>
    setValues((current) => ({ ...current, [key]: value }))

  const text = (key: keyof FormValues, extra?: { inputMode?: 'numeric' | 'decimal' }) => ({
    value: String(values[key]),
    onChange: (event: React.ChangeEvent<HTMLInputElement>) => set(key, event.target.value),
    ...extra,
  })

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    setFormError(null)
    const found = validate(values)
    setErrors(found)
    if (Object.keys(found).length > 0) return

    setSaving(true)
    try {
      const saved = await saveSettings(queryClient, toPayload(values))
      await onSaved(saved)
    } catch (error) {
      if (error instanceof ApiError && error.status === 422) {
        const mapped = serverErrors(error.body)
        setErrors(mapped)
        if (Object.keys(mapped).length === 0) setFormError('Settings were not saved. Try again.')
      } else {
        setFormError('Settings were not saved. Try again.')
      }
    } finally {
      setSaving(false)
    }
  }

  return (
    <form noValidate onSubmit={onSubmit} className="flex flex-col gap-8">
      <Section title="Business">
        <FormField id="name" label="Business name (required)" error={errors.name}>
          {(a11y) => <Input {...a11y} autoComplete="organization" {...text('name')} />}
        </FormField>
        <FormField id="currency" label="Currency" error={errors.currency}>
          {(a11y) => <Input {...a11y} maxLength={3} {...text('currency')} />}
        </FormField>
        <FormField id="timezone" label="Timezone" error={errors.timezone}>
          {(a11y) => <Input {...a11y} {...text('timezone')} />}
        </FormField>
        <FormField
          id="fy_start_month"
          label="Financial year starts in"
          error={errors.fy_start_month}
        >
          {(a11y) => (
            <Select
              {...a11y}
              value={values.fy_start_month}
              onChange={(event) => set('fy_start_month', event.target.value)}
            >
              {MONTHS.map((month, index) => (
                <option key={month} value={String(index + 1)}>
                  {month}
                </option>
              ))}
            </Select>
          )}
        </FormField>
      </Section>

      <Section title="GST">
        <div className="flex items-center gap-3">
          <Switch
            id="gst_registered"
            checked={values.gst_registered}
            onCheckedChange={(checked) => set('gst_registered', checked)}
          />
          <Label htmlFor="gst_registered">GST registered</Label>
        </div>
        <FormField id="gst_rate" label="GST rate (%)" error={errors.gst_rate}>
          {(a11y) => <Input {...a11y} {...text('gst_rate', { inputMode: 'decimal' })} />}
        </FormField>
      </Section>

      <Section title="Rules">
        <FormField id="price_rule" label="Price-change rule" error={errors.price_rule}>
          {(a11y) => (
            <Select
              {...a11y}
              value={values.price_rule}
              onChange={(event) => set('price_rule', event.target.value)}
            >
              {PRICE_RULES.map((rule) => (
                <option key={rule.value} value={rule.value}>
                  {rule.label}
                </option>
              ))}
            </Select>
          )}
        </FormField>
        <FormField
          id="dup_window_days"
          label="Duplicate window (days)"
          error={errors.dup_window_days}
        >
          {(a11y) => <Input {...a11y} {...text('dup_window_days', { inputMode: 'numeric' })} />}
        </FormField>
        <FormField
          id="reminder_days"
          label="Bill reminder lead (days)"
          error={errors.reminder_days}
        >
          {(a11y) => <Input {...a11y} {...text('reminder_days', { inputMode: 'numeric' })} />}
        </FormField>
      </Section>

      <Section title="Schedule">
        <FormField
          id="recap_time"
          label="Daily recap time"
          hint="24-hour time, HH:MM."
          error={errors.recap_time}
        >
          {(a11y) => <Input {...a11y} {...text('recap_time')} />}
        </FormField>
        <FormField id="report_day" label="Monthly report day" error={errors.report_day}>
          {(a11y) => <Input {...a11y} {...text('report_day', { inputMode: 'numeric' })} />}
        </FormField>
        <FormField
          id="report_time"
          label="Monthly report time"
          hint="24-hour time, HH:MM."
          error={errors.report_time}
        >
          {(a11y) => <Input {...a11y} {...text('report_time')} />}
        </FormField>
      </Section>

      {formError ? (
        <p role="alert" className="text-sm text-destructive">
          {formError}
        </p>
      ) : null}

      <div className="flex flex-col gap-3">
        <div>
          <Button type="submit" disabled={saving}>
            {saving ? <Spinner /> : null}
            {submitLabel}
          </Button>
        </div>
        {footer}
      </div>
    </form>
  )
}
