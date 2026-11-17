import type { BrowserContext } from '@playwright/test'

export const BOT_USERNAME = 'cafe_books_bot'

// TODO(P1-T07): replace route mocks with the real API started by playwright.config.ts webServer.
export async function mockApi(context: BrowserContext) {
  await context.route('**/api/config', (route) =>
    route.fulfill({ json: { bot_username: BOT_USERNAME, business_name: 'Kopi Corner' } }),
  )
  await context.route('https://t.me/**', (route) =>
    route.fulfill({ contentType: 'text/html', body: '<!doctype html><title>Telegram</title>' }),
  )
}
