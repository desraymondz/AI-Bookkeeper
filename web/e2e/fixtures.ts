import { test as base, expect, type Page } from '@playwright/test'
import { resetDatabase, seedPostingsFor } from './support/db.ts'
import { BOT_USERNAME } from './support/env.ts'

export { BOT_USERNAME, expect }

export const BUSINESS_NAME = 'Kopi Corner'

export const VALID_SETTINGS = {
  name: BUSINESS_NAME,
  currency: 'SGD',
  timezone: 'Asia/Singapore',
  fy_start_month: 1,
  gst_registered: true,
  gst_rate: '9.00',
  price_rule: 'any_change',
  dup_window_days: 180,
  reminder_days: 3,
  recap_time: '21:00',
  report_day: 1,
  report_time: '09:00',
}

export { resetDatabase, seedPostingsFor }

export async function signIn(page: Page) {
  const response = await page.request.post('/api/test/login')
  expect(response.ok()).toBe(true)
}

export async function configureBusiness(page: Page, overrides: Record<string, unknown> = {}) {
  const response = await page.request.put('/api/settings', {
    data: { ...VALID_SETTINGS, ...overrides },
  })
  expect(response.ok()).toBe(true)
}

export async function readSettings(page: Page) {
  const response = await page.request.get('/api/settings')
  return (await response.json()) as {
    configured: boolean
    settings: Record<string, unknown> | null
  }
}

export const test = base.extend<{ cleanDb: undefined }>({
  cleanDb: [
    async ({ context: _context }, use) => {
      await resetDatabase()
      await use(undefined)
    },
    { auto: true },
  ],
})
