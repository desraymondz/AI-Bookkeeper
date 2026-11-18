import { expect, test } from './fixtures.ts'
import { signIn } from './support/auth.ts'
import { configureBusiness } from './support/seed.ts'
import { linkBoss } from './support/telegram.ts'

test.beforeEach(async ({ page }) => {
  await signIn(page)
  await configureBusiness(page)
})

test('T-057 Connect Telegram shows link, Copy, Open in Telegram, QR and expiry', async ({
  page,
}) => {
  await page.goto('/settings/telegram')
  await expect(page.getByText('Not connected')).toBeVisible()
  await page.getByRole('button', { name: 'Connect Telegram' }).click()
  await expect(page.getByLabel('Telegram link')).toHaveValue(/t\.me\/cafe_books_bot\?start=/)
  await expect(page.getByRole('button', { name: 'Copy', exact: true })).toBeVisible()
  await expect(page.getByRole('main').getByRole('link', { name: 'Open in Telegram' })).toBeVisible()
  await expect(page.getByRole('img', { name: 'QR code' })).toBeVisible()
  await expect(page.getByText(/^Expires \d{1,2} \w{3} \d{4}, \d{2}:\d{2}$/)).toBeVisible()
})

test('T-063 Reconnect warns before making a new token', async ({ page }) => {
  await linkBoss(9001, 'meitan')
  await page.goto('/settings/telegram')
  await expect(page.getByText('Connected as @meitan')).toBeVisible()
  await page.getByRole('button', { name: 'Reconnect' }).click()
  const dialog = page.getByRole('dialog')
  await expect(
    dialog.getByText('Your current Telegram account will be disconnected.'),
  ).toBeVisible()
  await dialog.getByRole('button', { name: 'Create new link' }).click()
  await expect(page.getByLabel('Telegram link')).toBeVisible()
})
