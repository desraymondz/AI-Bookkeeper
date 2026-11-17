import { useQueryClient } from '@tanstack/react-query'
import { type FormEvent, useState } from 'react'
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
import { ApiError } from '@/lib/api'
import { ACCOUNT_TYPES, createAccount } from './api'

type Errors = { code?: string; name?: string; form?: string }

const CODE_PATTERN = /^[A-Za-z0-9.-]{1,16}$/

function mapServerErrors(error: unknown): Errors {
  if (!(error instanceof ApiError)) return { form: 'The account was not added. Try again.' }
  const body = error.body
  const detail = body && typeof body === 'object' && 'detail' in body ? body.detail : null
  if (Array.isArray(detail)) {
    const errors: Errors = {}
    for (const item of detail) {
      const field = item?.loc?.[item.loc.length - 1]
      if (field === 'code') {
        errors.code =
          error.status === 409
            ? 'This code is already used. Choose a different code.'
            : 'Use up to 16 letters, digits, dots or dashes.'
      } else if (field === 'name') {
        errors.name = 'Enter a name up to 200 characters.'
      }
    }
    if (Object.keys(errors).length > 0) return errors
  }
  return { form: 'The account was not added. Try again.' }
}

// See planning/02-design.md#settings (Chart of accounts)
export function AddAccountDialog({
  open,
  onOpenChange,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const queryClient = useQueryClient()
  const [code, setCode] = useState('')
  const [name, setName] = useState('')
  const [type, setType] = useState<string>('expense')
  const [errors, setErrors] = useState<Errors>({})
  const [saving, setSaving] = useState(false)

  function handleOpenChange(next: boolean) {
    if (!next) {
      setCode('')
      setName('')
      setType('expense')
      setErrors({})
    }
    onOpenChange(next)
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    const found: Errors = {}
    if (!CODE_PATTERN.test(code.trim()))
      found.code = 'Use up to 16 letters, digits, dots or dashes.'
    if (!name.trim()) found.name = 'Enter an account name.'
    setErrors(found)
    if (Object.keys(found).length > 0) return

    setSaving(true)
    try {
      await createAccount(queryClient, { code: code.trim(), name: name.trim(), type })
      toast.success('Account added')
      handleOpenChange(false)
    } catch (error) {
      setErrors(mapServerErrors(error))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add account</DialogTitle>
          <DialogDescription>New accounts are active and can be used right away.</DialogDescription>
        </DialogHeader>
        <form noValidate onSubmit={onSubmit} className="flex flex-col gap-4">
          <FormField id="account-code" label="Code (required)" error={errors.code}>
            {(a11y) => (
              <Input
                {...a11y}
                value={code}
                maxLength={16}
                onChange={(event) => setCode(event.target.value)}
              />
            )}
          </FormField>
          <FormField id="account-name" label="Name (required)" error={errors.name}>
            {(a11y) => (
              <Input {...a11y} value={name} onChange={(event) => setName(event.target.value)} />
            )}
          </FormField>
          <FormField id="account-type" label="Type">
            {(a11y) => (
              <Select {...a11y} value={type} onChange={(event) => setType(event.target.value)}>
                {ACCOUNT_TYPES.map((item) => (
                  <option key={item.value} value={item.value}>
                    {item.label}
                  </option>
                ))}
              </Select>
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
              Add account
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
