import { Client } from 'pg'
import { PG_E2E_URL } from './env.ts'

async function withClient<T>(run: (client: Client) => Promise<T>): Promise<T> {
  const client = new Client({ connectionString: PG_E2E_URL })
  await client.connect()
  try {
    return await run(client)
  } finally {
    await client.end()
  }
}

export function resetDatabase() {
  return withClient(async (client) => {
    const tables = await client.query<{ tablename: string }>(
      "SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename <> 'alembic_version'",
    )
    const names = tables.rows.map((row) => `"${row.tablename}"`).join(', ')
    await client.query(`TRUNCATE ${names} RESTART IDENTITY CASCADE`)
  })
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
