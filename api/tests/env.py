DUMMY_ENV: dict[str, str] = {
    "APP_ENV": "test",
    "DATABASE_URL": "postgresql+psycopg://bk:bk@127.0.0.1:1/bk",
    "PUBLIC_BASE_URL": "https://bot.example.com",
    "TELEGRAM_BOT_TOKEN": "123456:test-token",
    "TELEGRAM_BOT_USERNAME": "example_test_bot",
    "TELEGRAM_WEBHOOK_SECRET": "test_webhook_secret",
    "GOOGLE_CLIENT_ID": "test-client-id.apps.googleusercontent.com",
    "GOOGLE_CLIENT_SECRET": "test-client-secret",
    "GOOGLE_REDIRECT_URI": "http://localhost:5173/api/auth/callback",
    "BOSS_EMAIL": "boss@example.com",
    "SESSION_SECRET": "test-session-secret",
    "GEMINI_API_KEY": "test-gemini-key",
}
