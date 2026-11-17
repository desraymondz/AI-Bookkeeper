import { expect, type Page } from '@playwright/test'
import { withClient } from './db.ts'

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

export function seedPostingsFor(accountName: string) {
  return withClient(async (client) => {
    const account = await client.query<{ id: number }>('SELECT id FROM accounts WHERE name = $1', [
      accountName,
    ])
    const cash = await client.query<{ id: number }>("SELECT id FROM accounts WHERE name = 'Cash'")
    const entry = await client.query<{ id: number }>(
      `INSERT INTO journal_entries (entry_no, date, description, source, status, kind, posted_at)
       VALUES (1, CURRENT_DATE, 'E2E seed entry', 'manual', 'posted', 'normal', now())
       RETURNING id`,
    )
    const entryId = entry.rows[0].id
    await client.query(
      `INSERT INTO journal_lines (entry_id, line_no, account_id, debit, credit)
       VALUES ($1, 1, $2, 10.00, 0), ($1, 2, $3, 0, 10.00)`,
      [entryId, account.rows[0].id, cash.rows[0].id],
    )
  })
}
