import { HttpResponse, http } from 'msw'
import { setupServer } from 'msw/node'

export const TEST_BOT_USERNAME = 'cafe_books_bot'

export const handlers = [
  http.get('*/api/config', () =>
    HttpResponse.json({ bot_username: TEST_BOT_USERNAME, business_name: 'Kopi Corner' }),
  ),
]

export const server = setupServer(...handlers)
