import { ensureDatabase, migrateDatabase } from './db.ts'

// See planning/decisions.md#D-031
export default async function globalSetup() {
  await ensureDatabase()
  migrateDatabase()
}
