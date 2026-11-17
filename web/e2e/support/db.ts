import { spawnSync } from 'node:child_process'
import path from 'node:path'
import { Client } from 'pg'
import { API_DATABASE_URL, E2E_DB_NAME, PG_ADMIN_URL, PG_E2E_URL } from './env.ts'

export async function withClient<T>(run: (client: Client) => Promise<T>): Promise<T> {
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

export async function ensureDatabase() {
  const admin = new Client({ connectionString: PG_ADMIN_URL })
  await admin.connect()
  try {
    const found = await admin.query('SELECT 1 FROM pg_database WHERE datname = $1', [E2E_DB_NAME])
    if (found.rowCount === 0) await admin.query(`CREATE DATABASE "${E2E_DB_NAME}"`)
  } finally {
    await admin.end()
  }
}

export function migrateDatabase() {
  const migrate = spawnSync('uv', ['run', 'alembic', 'upgrade', 'head'], {
    cwd: path.resolve(import.meta.dirname, '../../../api'),
    env: { ...process.env, APP_ENV: 'test', DATABASE_URL: API_DATABASE_URL },
    stdio: 'inherit',
  })
  if (migrate.status !== 0) throw new Error('alembic upgrade head failed for the e2e database')
}
