import { useQueryClient } from '@tanstack/react-query'
import { type FormEvent, useEffect, useState } from 'react'
import { toast } from 'sonner'
import { FormField } from '@/components/form-field'
import { Spinner } from '@/components/states'
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
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { useAccounts } from '@/features/accounts/api'
import { ApiError } from '@/lib/api'
import { createSupplier, type Supplier, updateSupplier } from './api'

type Errors = { name?: string; account?: string; terms?: string; form?: string }

type Values = { name: string; account: string; uen: string; terms: string; hint: string }

function initial(supplier: Supplier | null): Values {
  return {
    name: supplier?.name ?? '',
    account: supplier ? String(supplier.default_account_id) : '',
    uen: supplier?.uen ?? '',
    terms: String(supplier?.terms_days ?? 30),
    hint: supplier?.telegram_username_hint ?? '',
  }
}

function mapServerErrors(error: unknown, fallback: string): Errors {
  if (error instanceof ApiError) {
    const body = error.body
    const detail = body && typeof body === 'object' && 'detail' in body ? body.detail : null
    if (Array.isArray(detail)) {
      const errors: Errors = {}
      for (const item of detail) {
        const field = item?.loc?.[item.loc.length - 1]
        if (field === 'name') errors.name = 'Enter a name up to 200 characters.'
        if (field === 'default_account_id') errors.account = 'Choose an active expense account.'
        if (field === 'terms_days') errors.terms = 'Enter whole days from 0 to 3650.'
      }
      if (Object.keys(errors).length > 0) return errors
    }
  }
  return { form: fallback }
}

// See planning/01-prd.md#F-007 (F-007.1) and planning/02-design.md#settings (Suppliers)
export function SupplierDialog({
  supplier,
  open,
  onOpenChange,
}: {
  supplier: Supplier | null
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const queryClient = useQueryClient()
  const accounts = useAccounts()
  const [values, setValues] = useState<Values>(() => initial(supplier))
  const [errors, setErrors] = useState<Errors>({})
  const [saving, setSaving] = useState(false)
  const editing = supplier !== null

  useEffect(() => {
    if (open) {
      setValues(initial(supplier))
      setErrors({})
    }
  }, [open, supplier])

  const expenseAccounts = (accounts.data ?? []).filter(
    (account) =>
      account.type === 'expense' && (account.active || account.id === supplier?.default_account_id),
  )

  function set<K extends keyof Values>(key: K, value: Values[K]) {
    setValues((current) => ({ ...current, [key]: value }))
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    const found: Errors = {}
    if (!values.name.trim()) found.name = 'Enter a supplier name.'
    if (!values.account) found.account = 'Choose a default account.'
    const terms = Number(values.terms)
    if (values.terms.trim() === '' || !Number.isInteger(terms) || terms < 0 || terms > 3650)
      found.terms = 'Enter whole days from 0 to 3650.'
    setErrors(found)
    if (Object.keys(found).length > 0) return

    const body = {
      name: values.name.trim(),
      default_account_id: Number(values.account),
      uen: values.uen.trim(),
      terms_days: terms,
      telegram_username_hint: values.hint.trim(),
    }
    setSaving(true)
    try {
      if (supplier) await updateSupplier(queryClient, supplier.id, body)
      else await createSupplier(queryClient, body)
      toast.success(editing ? 'Supplier saved' : 'Supplier added')
      onOpenChange(false)
    } catch (error) {
      setErrors(
        mapServerErrors(
          error,
          editing
            ? 'The supplier was not saved. Try again.'
            : 'The supplier was not added. Try again.',
        ),
      )
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{editing ? 'Edit supplier' : 'Add supplier'}</DialogTitle>
          <DialogDescription>
            Invoices from this supplier are posted to the default account.
          </DialogDescription>
        </DialogHeader>
        <form noValidate onSubmit={onSubmit} className="flex flex-col gap-4">
          <FormField id="supplier-name" label="Name (required)" error={errors.name}>
            {(a11y) => (
              <Input
                {...a11y}
                value={values.name}
                onChange={(event) => set('name', event.target.value)}
              />
            )}
          </FormField>
          <FormField
            id="supplier-account"
            label="Default account (required)"
            error={errors.account}
          >
            {(a11y) => (
              <Select
                {...a11y}
                value={values.account}
                onChange={(event) => set('account', event.target.value)}
              >
                <option value="">Choose an account</option>
                {expenseAccounts.map((account) => (
                  <option key={account.id} value={account.id}>
                    {account.name}
                  </option>
                ))}
              </Select>
            )}
          </FormField>
          <FormField id="supplier-uen" label="UEN">
            {(a11y) => (
              <Input
                {...a11y}
                value={values.uen}
                maxLength={32}
                onChange={(event) => set('uen', event.target.value)}
              />
            )}
          </FormField>
          <FormField id="supplier-terms" label="Payment terms (days)" error={errors.terms}>
            {(a11y) => (
              <Input
                {...a11y}
                inputMode="numeric"
                value={values.terms}
                onChange={(event) => set('terms', event.target.value)}
              />
            )}
          </FormField>
          <FormField id="supplier-hint" label="Telegram username hint">
            {(a11y) => (
              <Input
                {...a11y}
                value={values.hint}
                maxLength={64}
                onChange={(event) => set('hint', event.target.value)}
              />
            )}
          </FormField>
          {errors.form ? (
            <p role="alert" className="text-sm text-destructive">
              {errors.form}
            </p>
          ) : null}
          <DialogFooter>
            <DialogClose asChild>
              <Button type="button" variant="secondary">
                Cancel
              </Button>
            </DialogClose>
            <Button type="submit" disabled={saving}>
              {saving ? <Spinner /> : null}
              {editing ? 'Save' : 'Add supplier'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
