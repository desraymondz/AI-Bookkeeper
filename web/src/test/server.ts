import { HttpResponse, http } from 'msw'
import { setupServer } from 'msw/node'

export const TEST_BOT_USERNAME = 'cafe_books_bot'
export const TEST_EMAIL = 'boss@example.com'

export const TEST_DEFAULTS = {
  name: '',
  currency: 'SGD',
  timezone: 'Asia/Singapore',
  fy_start_month: 1,
  gst_registered: false,
  gst_rate: '9.00',
  price_rule: 'any_change',
  dup_window_days: 180,
  reminder_days: 3,
  recap_time: '21:00',
  report_day: 1,
  report_time: '09:00',
}

export const TEST_SETTINGS = { ...TEST_DEFAULTS, name: 'Kopi Corner' }

export const handlers = [
  http.get('*/api/config', () =>
    HttpResponse.json({ bot_username: TEST_BOT_USERNAME, business_name: 'Kopi Corner' }),
  ),
  http.get('*/api/auth/me', () => HttpResponse.json({ email: TEST_EMAIL })),
  http.post('*/api/auth/logout', () => new HttpResponse(null, { status: 204 })),
  http.get('*/api/links/boss', () =>
    HttpResponse.json({ connected: false, username: null, display_name: null, linked_at: null }),
  ),
  http.get('*/api/journal', () =>
    HttpResponse.json({
      start: '2026-11-01',
      end: '2026-11-18',
      entries: [],
      total_debit: '0.00',
      total_credit: '0.00',
    }),
  ),
  http.get('*/api/settings', () =>
    HttpResponse.json({ configured: true, settings: TEST_SETTINGS, defaults: TEST_DEFAULTS }),
  ),
]

export const server = setupServer(...handlers)
