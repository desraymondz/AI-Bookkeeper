import { expect, test } from './fixtures.ts'
import { signIn } from './support/auth.ts'
import { configureBusiness } from './support/seed.ts'
import { addSupplier } from './support/telegram.ts'

test.beforeEach(async ({ page }) => {
  await signIn(page)
  await configureBusiness(page)
})

test('T-065 adding Ocean Fresh shows the row as Active', async ({ page }) => {
  await page.goto('/settings/suppliers')
  await page.getByRole('button', { name: 'Add supplier' }).click()
  const dialog = page.getByRole('dialog')
  await dialog.getByLabel('Name (required)').fill('Ocean Fresh')
  await dialog.getByLabel('Default account (required)').selectOption({ label: 'COGS Seafood' })
  await dialog.getByLabel('UEN').fill('201912345K')
  await dialog.getByLabel('Payment terms (days)').fill('30')
  await dialog.getByLabel('Telegram username hint').fill('@oceanfresh')
  await dialog.getByRole('button', { name: 'Add supplier' }).click()
  const row = page.getByRole('row', { name: /Ocean Fresh/ })
  await expect(row).toBeVisible()
  await expect(row.getByText('Active')).toBeVisible()
  await expect(row.getByText('201912345K')).toBeVisible()
  await expect(row.getByText('@oceanfresh')).toBeVisible()
})

test('T-066 empty name or account shows inline errors and adds nothing', async ({ page }) => {
  await page.goto('/settings/suppliers')
  await page.getByRole('button', { name: 'Add supplier' }).click()
  const dialog = page.getByRole('dialog')
  await dialog.getByRole('button', { name: 'Add supplier' }).click()
  await expect(dialog.getByText('Enter a supplier name.')).toBeVisible()
  await expect(dialog.getByText('Choose a default account.')).toBeVisible()
  await dialog.getByRole('button', { name: 'Cancel' }).click()
  const response = await page.request.get('/api/suppliers')
  expect(await response.json()).toEqual([])
})

test('T-067 Create invite shows link, expiry, single-use note and copies', async ({
  page,
  context,
}) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write'])
  await addSupplier(page, 'Ocean Fresh')
  await page.goto('/settings/suppliers')
  await page.getByRole('button', { name: 'Actions for Ocean Fresh' }).click()
  await page.getByRole('menuitem', { name: 'Create invite' }).click()
  const dialog = page.getByRole('dialog')
  const link = dialog.getByLabel('Invite link')
  await expect(link).toHaveValue(/t\.me\/cafe_books_bot\?start=/)
  await expect(dialog.getByText(/^Expires \d{1,2} \w{3} \d{4}, \d{2}:\d{2}$/)).toBeVisible()
  await expect(dialog.getByText(/can be used once/)).toBeVisible()
  await dialog.getByRole('button', { name: 'Copy link' }).click()
  await expect(page.getByText('Link copied')).toBeVisible()
})
