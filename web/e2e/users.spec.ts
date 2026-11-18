import { expect, test } from './fixtures.ts'
import { signIn } from './support/auth.ts'
import { configureBusiness } from './support/seed.ts'
import { addSupplier, linkBoss, linkSupplierUser } from './support/telegram.ts'

test.beforeEach(async ({ page }) => {
  await signIn(page)
  await configureBusiness(page)
  await linkBoss(9001, 'meitan')
  const ocean = await addSupplier(page, 'Ocean Fresh')
  await addSupplier(page, 'Dairy Best')
  await linkSupplierUser(ocean.id, 9002, 'oceanrep')
})

test('T-071 users table shows role, supplier, status and linked date', async ({ page }) => {
  await page.goto('/settings/users')
  const boss = page.getByRole('row', { name: /@meitan/ })
  await expect(boss.getByText('Boss')).toBeVisible()
  const supplier = page.getByRole('row', { name: /@oceanrep/ })
  await expect(supplier.getByText('Supplier', { exact: true })).toBeVisible()
  await expect(supplier.getByText('Ocean Fresh')).toBeVisible()
  await expect(supplier.getByText('Active')).toBeVisible()
  await expect(supplier.getByText(/^\d{1,2} \w{3} \d{4}$/)).toBeVisible()
})

test('T-072 Change linked supplier shows Dairy Best', async ({ page }) => {
  await page.goto('/settings/users')
  await page.getByRole('button', { name: /^Actions for .*oceanrep|^Actions for Ocean/ }).click()
  await page.getByRole('menuitem', { name: 'Change linked supplier' }).click()
  const dialog = page.getByRole('dialog')
  await dialog.getByLabel('Supplier').selectOption({ label: 'Dairy Best' })
  await dialog.getByRole('button', { name: 'Save' }).click()
  await expect(page.getByRole('row', { name: /@oceanrep/ }).getByText('Dairy Best')).toBeVisible()
})

test('T-073 Deactivate shows the new status', async ({ page }) => {
  await page.goto('/settings/users')
  await page
    .getByRole('row', { name: /@oceanrep/ })
    .getByRole('button')
    .click()
  await page.getByRole('menuitem', { name: 'Deactivate' }).click()
  await page.getByRole('dialog').getByRole('button', { name: 'Deactivate' }).click()
  await expect(page.getByRole('row', { name: /@oceanrep/ }).getByText('Deactivated')).toBeVisible()
})

test('T-074 boss row menu has no destructive actions', async ({ page }) => {
  await page.goto('/settings/users')
  await page
    .getByRole('row', { name: /@meitan/ })
    .getByRole('button')
    .click()
  await expect(page.getByRole('menu')).toBeVisible()
  await expect(page.getByRole('menuitem', { name: /Deactivate|Revoke/ })).toHaveCount(0)
  await expect(page.getByText('There is exactly one boss.')).toBeVisible()
})
