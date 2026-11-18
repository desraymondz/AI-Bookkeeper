import { expect, type Page } from '@playwright/test'
import { withClient } from './db.ts'

export async function expenseAccountId(page: Page, name: string) {
  const response = await page.request.get('/api/accounts')
  const rows = (await response.json()) as { id: number; name: string }[]
  const found = rows.find((row) => row.name === name)
  expect(found).toBeDefined()
  return (found as { id: number }).id
}

export async function addSupplier(page: Page, name: string, account = 'COGS Seafood') {
  const response = await page.request.post('/api/suppliers', {
    data: { name, default_account_id: await expenseAccountId(page, account) },
  })
  expect(response.ok()).toBe(true)
  return (await response.json()) as { id: number }
}

// Telegram is unreachable in e2e, so bindings are written to users directly (no journal rows).
export function linkSupplierUser(supplierId: number, userId: number, username: string) {
  return withClient((client) =>
    client.query(
      `INSERT INTO users (telegram_user_id, username, display_name, role, supplier_id, status, linked_at)
       VALUES ($1, $2, $2, 'supplier', $3, 'active', now())`,
      [userId, username, supplierId],
    ),
  )
}

export function linkBoss(userId: number, username: string) {
  return withClient(async (client) => {
    const updated = await client.query(
      `UPDATE users SET telegram_user_id = $1, username = $2, display_name = $2, linked_at = now()
       WHERE role = 'boss' AND status = 'active'`,
      [userId, username],
    )
    if (updated.rowCount === 0) {
      await client.query(
        `INSERT INTO users (telegram_user_id, username, display_name, role, status, linked_at)
         VALUES ($1, $2, $2, 'boss', 'active', now())`,
        [userId, username],
      )
    }
  })
}
