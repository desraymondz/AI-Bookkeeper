import { spawnSync } from 'node:child_process'
import path from 'node:path'
import { Client } from 'pg'
import { API_DATABASE_URL, E2E_DB_NAME, PG_ADMIN_URL } from './env.ts'

// See planning/03-tech-stack.md#12-testing-strategy
export default async function globalSetup() {
  const admin = new Client({ connectionString: PG_ADMIN_URL })
  await admin.connect()
  try {
    const found = await admin.query('SELECT 1 FROM pg_database WHERE datname = $1', [E2E_DB_NAME])
    if (found.rowCount === 0) await admin.query(`CREATE DATABASE "${E2E_DB_NAME}"`)
  } finally {
    await admin.end()
  }

  const migrate = spawnSync('uv', ['run', 'alembic', 'upgrade', 'head'], {
    cwd: path.resolve(import.meta.dirname, '../../../api'),
    env: { ...process.env, APP_ENV: 'test', DATABASE_URL: API_DATABASE_URL },
    stdio: 'inherit',
  })
  if (migrate.status !== 0) throw new Error('alembic upgrade head failed for the e2e database')
}
