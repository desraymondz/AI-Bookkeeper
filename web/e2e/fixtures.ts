import { test as base, expect } from '@playwright/test'
import { resetDatabase } from './support/db.ts'

export { expect }

export const test = base.extend<{ cleanDb: undefined }>({
  cleanDb: [
    async ({ context: _context }, use) => {
      await resetDatabase()
      await use(undefined)
    },
    { auto: true },
  ],
})
