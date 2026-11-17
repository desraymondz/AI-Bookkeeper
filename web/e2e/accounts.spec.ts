import { expect, test } from './fixtures.ts'
import { signIn } from './support/auth.ts'
import { configureBusiness, seedPostingsFor } from './support/seed.ts'

test.beforeEach(async ({ page }) => {
  await signIn(page)
  await configureBusiness(page)
})

async function addAccount(page: import('@playwright/test').Page, code: string, name: string) {
  await page.getByRole('button', { name: 'Add account' }).click()
  const dialog = page.getByRole('dialog')
  await dialog.getByLabel('Code (required)').fill(code)
  await dialog.getByLabel('Name (required)').fill(name)
  await dialog.getByLabel('Type').selectOption({ label: 'Expense' })
  await dialog.getByRole('button', { name: 'Add account' }).click()
  return dialog
}

test('T-039 adding account 6100 Ice shows it as Active', async ({ page }) => {
  await page.goto('/settings/accounts')
  await addAccount(page, '6100', 'Ice')
  const row = page.getByRole('row', { name: /6100.*Ice/ })
  await expect(row).toBeVisible()
  await expect(row.getByText('Active')).toBeVisible()
})

test('T-040 duplicate code shows an inline error and adds nothing', async ({ page }) => {
  await page.goto('/settings/accounts')
  const before = await page.getByRole('row').count()
  const dialog = await addAccount(page, '5000', 'Another Seafood')
  await expect(dialog.getByText(/already used/)).toBeVisible()
  await dialog.getByRole('button', { name: 'Cancel' }).click()
  await expect(page.getByRole('row')).toHaveCount(before)
  await expect(page.getByText('Another Seafood')).toHaveCount(0)
})

test('T-041 deactivated account is hidden unless Show inactive is on', async ({ page }) => {
  await page.goto('/settings/accounts')
  await addAccount(page, '6100', 'Ice')
  await expect(page.getByRole('row', { name: /6100.*Ice/ })).toBeVisible()

  await page.getByRole('button', { name: 'Actions for 6100 Ice' }).click()
  await page.getByRole('menuitem', { name: 'Deactivate' }).click()
  await expect(page.getByRole('row', { name: /6100.*Ice/ })).toHaveCount(0)

  await page.getByRole('switch', { name: 'Show inactive' }).click()
  const row = page.getByRole('row', { name: /6100.*Ice/ })
  await expect(row).toBeVisible()
  await expect(row.getByText('Inactive')).toBeVisible()
})

test('T-042 account with postings cannot be deactivated', async ({ page }) => {
  await seedPostingsFor('COGS Seafood')
  await page.goto('/settings/accounts')
  await page.getByRole('button', { name: 'Actions for 5000 COGS Seafood' }).click()

  const deactivate = page.getByRole('menuitem', { name: 'Deactivate' })
  await expect(deactivate).toHaveAttribute('aria-disabled', 'true')
  await deactivate.hover({ force: true })
  await expect(page.getByRole('tooltip').getByText('Has postings')).toBeVisible()
  await expect(page.getByRole('menuitem')).toHaveCount(1)
})
