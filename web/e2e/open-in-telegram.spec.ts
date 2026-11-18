import { expect, test } from './fixtures.ts'
import { signIn } from './support/auth.ts'
import { BOT_USERNAME } from './support/env.ts'
import { configureBusiness } from './support/seed.ts'

const telegramUrl = `https://t.me/${BOT_USERNAME}`

test.describe('T-208 header Open in Telegram', () => {
  test.beforeEach(async ({ page, context }) => {
    await signIn(page)
    await configureBusiness(page)
    await context.route('https://t.me/**', (route) =>
      route.fulfill({ contentType: 'text/html', body: '<!doctype html><title>Telegram</title>' }),
    )
  })

  test('opens t.me/<bot username> in a new tab', async ({ page, context }) => {
    await page.setViewportSize({ width: 1280, height: 800 })
    await page.goto('/accounting/journal?range=this-month')

    const link = page.getByRole('banner').getByRole('link', { name: 'Open in Telegram' })
    await expect(link).toHaveAttribute('href', telegramUrl)

    const [popup] = await Promise.all([context.waitForEvent('page'), link.click()])
    await popup.waitForLoadState()
    expect(popup.url()).toBe(telegramUrl)
    expect(page.url()).toContain('/accounting/journal')
  })

  test('at 375px width the button is inside the nav sheet', async ({ page, context }) => {
    await page.setViewportSize({ width: 375, height: 812 })
    await page.goto('/accounting/journal?range=this-month')

    const header = page.getByRole('banner')
    await expect(header.getByRole('link', { name: 'Open in Telegram' })).toHaveCount(0)

    await header.getByRole('button', { name: 'Open menu' }).click()
    const sheet = page.getByRole('dialog')
    const link = sheet.getByRole('link', { name: 'Open in Telegram' })
    await expect(link).toHaveAttribute('href', telegramUrl)

    const [popup] = await Promise.all([context.waitForEvent('page'), link.click()])
    await popup.waitForLoadState()
    expect(popup.url()).toBe(telegramUrl)
  })
})
