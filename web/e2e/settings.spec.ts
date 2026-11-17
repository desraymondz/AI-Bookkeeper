import { expect, test } from './fixtures.ts'
import { signIn } from './support/auth.ts'
import { configureBusiness, readSettings } from './support/seed.ts'

test.beforeEach(async ({ page }) => {
  await signIn(page)
  await configureBusiness(page)
})

test('T-037 business settings show the new-events note', async ({ page }) => {
  await page.goto('/settings/business')
  await expect(page.getByText('Changes apply to new events only.')).toBeVisible()
})

test('business settings save with a toast', async ({ page }) => {
  await page.goto('/settings/business')
  await page.getByLabel('Business name (required)').fill('Kopi Corner Two')
  await page.getByRole('button', { name: 'Save' }).click()
  await expect(page.getByText('Settings saved')).toBeVisible()
  await expect(page.getByRole('banner').getByText('Kopi Corner Two')).toBeVisible()
})

for (const rate of ['101', '-1']) {
  test(`T-033 business rejects GST rate ${rate} and saves nothing`, async ({ page }) => {
    await page.goto('/settings/business')
    await page.getByLabel('GST rate (%)').fill(rate)
    await page.getByRole('button', { name: 'Save' }).click()
    await expect(page.getByText('GST rate must be a number from 0 to 100.')).toBeVisible()

    await page.reload()
    await expect(page.getByLabel('GST rate (%)')).toHaveValue('9')
    expect((await readSettings(page)).settings?.gst_rate).toBe('9.00')
  })
}

for (const time of ['25:00', '9pm']) {
  test(`T-034 business rejects recap time ${time} and saves no field`, async ({ page }) => {
    await page.goto('/settings/business')
    await page.getByLabel('Business name (required)').fill('Changed Name')
    await page.getByLabel('Daily recap time').fill(time)
    await page.getByRole('button', { name: 'Save' }).click()
    await expect(page.getByText('Use HH:MM, for example 21:00.')).toBeVisible()

    await page.reload()
    await expect(page.getByLabel('Business name (required)')).toHaveValue('Kopi Corner')
    await expect(page.getByLabel('Daily recap time')).toHaveValue('21:00')
    expect((await readSettings(page)).settings?.name).toBe('Kopi Corner')
  })
}
