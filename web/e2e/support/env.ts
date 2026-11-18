import path from 'node:path'

// See planning/decisions.md#D-031 and planning/03-tech-stack.md#12-testing-strategy
const worktreeName = path.basename(path.resolve(import.meta.dirname, '../../..'))

function stableHash(value: string): number {
  let hash = 2166136261
  for (const char of value) {
    hash ^= char.codePointAt(0) ?? 0
    hash = Math.imul(hash, 16777619) >>> 0
  }
  return hash
}

function slugOf(value: string): string {
  return (
    value
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '_')
      .replace(/^_+|_+$/g, '')
      .slice(0, 40) || 'main'
  )
}

const offset = stableHash(worktreeName) % 2000

export const API_PORT = Number(process.env.E2E_API_PORT ?? 20000 + offset)
export const WEB_PORT = Number(process.env.E2E_WEB_PORT ?? 22000 + offset)
export const E2E_DB_NAME = process.env.E2E_DB_NAME ?? `bookkeeper_e2e_${slugOf(worktreeName)}`

const PG_BASE = process.env.E2E_PG_URL ?? 'postgresql://bookkeeper:bookkeeper@127.0.0.1:5432'

export const PG_ADMIN_URL = `${PG_BASE}/postgres`
export const PG_E2E_URL = `${PG_BASE}/${E2E_DB_NAME}`
export const API_DATABASE_URL = PG_E2E_URL.replace(/^postgresql:/, 'postgresql+psycopg:')

export const BOT_USERNAME = 'cafe_books_bot'
export const BOSS_EMAIL = 'boss@example.com'

export const API_ENV: Record<string, string> = {
  APP_ENV: 'test',
  E2E_TEST_LOGIN: '1',
  DATABASE_URL: API_DATABASE_URL,
  PUBLIC_BASE_URL: `http://localhost:${WEB_PORT}`,
  WEB_APP_URL: `http://localhost:${WEB_PORT}`,
  TELEGRAM_BOT_TOKEN: '123456:e2e-token',
  TELEGRAM_BOT_USERNAME: BOT_USERNAME,
  TELEGRAM_WEBHOOK_SECRET: 'e2e-webhook-secret',
  GOOGLE_CLIENT_ID: 'e2e-client-id.apps.googleusercontent.com',
  GOOGLE_CLIENT_SECRET: 'e2e-client-secret',
  GOOGLE_REDIRECT_URI: `http://localhost:${WEB_PORT}/api/auth/callback`,
  BOSS_EMAIL,
  SESSION_SECRET: 'e2e-session-secret',
  GEMINI_API_KEY: 'e2e-gemini-key',
}
