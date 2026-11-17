import path from 'node:path'
import { defineConfig, devices } from '@playwright/test'
import { API_ENV, API_PORT, WEB_PORT } from './e2e/support/env.ts'

// See planning/03-tech-stack.md#12-testing-strategy
export default defineConfig({
  testDir: './e2e',
  globalSetup: './e2e/support/global-setup.ts',
  fullyParallel: false,
  workers: 1,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI ? 'github' : 'list',
  use: {
    baseURL: `http://localhost:${WEB_PORT}`,
    trace: 'on-first-retry',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: [
    {
      command: `uv run uvicorn bookkeeper.main:app --port ${API_PORT}`,
      cwd: path.resolve(import.meta.dirname, '../api'),
      url: `http://localhost:${API_PORT}/openapi.json`,
      env: API_ENV,
      reuseExistingServer: false,
      timeout: 60_000,
    },
    {
      command: `pnpm exec vite --port ${WEB_PORT} --strictPort`,
      url: `http://localhost:${WEB_PORT}`,
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
    },
  ],
})
