import { expect, readSettings, signIn, test } from './fixtures.ts'

test.beforeEach(async ({ page }) => {
  await signIn(page)
})

test('T-030 unconfigured boss is sent to /setup with disabled nav', async ({ page }) => {
  await page.goto('/analytics?range=this-month')
  await expect(page).toHaveURL(/\/setup$/)
  const nav = page.getByRole('navigation', { name: 'Main' })
  await expect(nav.getByRole('link')).toHaveCount(0)
  for (const label of ['Accounting', 'Analytics', 'Settings']) {
    await expect(nav.getByText(label)).toHaveAttribute('aria-disabled', 'true')
  }
})

test('T-031 setup pre-fills the defaults', async ({ page }) => {
  await page.goto('/setup')
  await expect(page.getByLabel('Currency')).toHaveValue('SGD')
  await expect(page.getByLabel('Timezone')).toHaveValue('Asia/Singapore')
  await expect(page.getByLabel('GST rate (%)')).toHaveValue('9')
  await expect(page.getByLabel('Price-change rule')).toHaveValue('any_change')
  await expect(page.getByLabel('Price-change rule')).toContainText('Any unit price change')
  await expect(page.getByLabel('Duplicate window (days)')).toHaveValue('180')
  await expect(page.getByLabel('Bill reminder lead (days)')).toHaveValue('3')
  await expect(page.getByLabel('Daily recap time')).toHaveValue('21:00')
  await expect(page.getByLabel('Monthly report day')).toHaveValue('1')
  await expect(page.getByLabel('Monthly report time')).toHaveValue('09:00')
})

test('T-032 valid setup saves, toasts and persists', async ({ page }) => {
  await page.goto('/setup')
  await page.getByLabel('Business name (required)').fill('Kopi Corner')
  await page.getByLabel('Duplicate window (days)').fill('120')
  await page.getByRole('button', { name: 'Save and continue' }).click()

  await expect(page).toHaveURL(/\/settings\/telegram$/)
  await expect(page.getByText('Settings saved')).toBeVisible()

  await page.goto('/settings/business')
  await page.reload()
  await expect(page.getByLabel('Business name (required)')).toHaveValue('Kopi Corner')
  await expect(page.getByLabel('Duplicate window (days)')).toHaveValue('120')
})

for (const rate of ['101', '-1']) {
  test(`T-033 setup rejects GST rate ${rate} and saves nothing`, async ({ page }) => {
    await page.goto('/setup')
    await page.getByLabel('Business name (required)').fill('Kopi Corner')
    await page.getByLabel('GST rate (%)').fill(rate)
    await page.getByRole('button', { name: 'Save and continue' }).click()

    await expect(page.getByText('GST rate must be a number from 0 to 100.')).toBeVisible()
    await expect(page.getByLabel('GST rate (%)')).toHaveAttribute('aria-invalid', 'true')
    await expect(page).toHaveURL(/\/setup$/)

    await page.reload()
    await expect(page.getByLabel('Business name (required)')).toHaveValue('')
    expect((await readSettings(page)).configured).toBe(false)
  })
}
