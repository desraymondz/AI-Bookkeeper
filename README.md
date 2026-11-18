# AI Bookkeeper

A Telegram bookkeeper for one small business (the demo is a Singapore cafe). Suppliers send invoices to the bot. The bot reads each one with Gemini, proposes a double-entry journal entry, and runs ten deterministic checks in code. A clean invoice posts on its own and the boss gets a short FYI. Anything that looks wrong waits for the boss with Approve, Edit and Reject buttons. The boss can also ask questions, record cash expenses and sales, mark bills paid and pull a daily recap, all in chat. A read-only web dashboard shows the books.

The model proposes and code decides: nothing posts unless every check passes or the boss approves, and every journal write goes through one ledger posting service that enforces debits = credits, open periods and immutability.

## What works in this prototype

| Area | Built |
| --- | --- |
| Telegram linking | Boss and supplier deep links (`/start <token>`), strangers get a neutral reply and the boss gets Ignore / Add / Block |
| Invoice pipeline | PDF and photo intake, Gemini extraction, 10 checks (known supplier, arithmetic, GST, balanced, duplicate, revision, price change, period, sanity, suspicious content), auto-post with FYI, approval card with Approve / Edit / Reject, bills |
| Boss chat | Questions about spend, sales, bills and balances; "paid 50 cash for ice today"; "sales today 1,850, cash 420, card 1,430"; `/bills` with Mark paid; `/recap` |
| Web | Google sign-in for one boss, settings, chart of accounts, suppliers, users, Telegram connection, Journal with entry detail sheet, Trial balance, P&L, Balance sheet |
| Eval | `bk eval` runs clean and trap invoices through the real pipeline and prints a pass/fail table |

Deferred to v1 (see `planning/decisions.md#D-036`): opening balances form, Excel migration, scheduled recap and bill reminders, partial payments and mark paid by text, reversal by chat, fixed assets and depreciation, month-end close and PDF report pack, general ledger, adjusted trial balance and cash flow tabs, analytics, the full 13-trap eval set, production compose profile.

## Credentials to create

Put every value in `.env` at the repo root (`make setup` copies `.env.example` there). The API refuses to start and names the missing variable if one is absent.

| Variable | How to get it |
| --- | --- |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_BOT_USERNAME` | In Telegram open @BotFather, send `/newbot`, pick a display name and a username ending in `bot`. Copy the token, and the username without `@`. |
| `TELEGRAM_WEBHOOK_SECRET` | Any random string, for example `openssl rand -hex 32`. Telegram sends it back on every webhook call. |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI` | At console.cloud.google.com create a project. Set up the OAuth consent screen (External, scopes `openid`, `email`, `profile`, add your Google account as a test user). Then Credentials, Create OAuth client ID, Web application. Authorized JavaScript origin `http://localhost:5173`, redirect URI `http://localhost:5173/api/auth/callback`. Use that URI as `GOOGLE_REDIRECT_URI`. |
| `BOSS_EMAIL` | The one Google account allowed to sign in to the web. |
| `SESSION_SECRET` | `openssl rand -hex 32`. |
| `GEMINI_API_KEY` | aistudio.google.com, Get API key, Create key. Model names come from `GEMINI_MODEL_*` (defaults in `.env.example`). |
| `DATABASE_URL` | The local Postgres from `docker-compose.yml`: `postgresql+psycopg://bookkeeper:bookkeeper@127.0.0.1:5432/bookkeeper`. |
| `PUBLIC_BASE_URL` | The public HTTPS URL that reaches the API on port 8000. In dev this is your ngrok URL, for example `https://your-name.ngrok-free.app`. |
| ngrok | Sign up at ngrok.com and run `ngrok config add-authtoken <token>`. Optional: claim the free static domain and export `NGROK_DOMAIN` so the URL never changes. |

## Run it locally

Needs Docker, Python 3.14 with `uv`, Node with `pnpm`, and ngrok.

```bash
make setup
```

```bash
make db
```

```bash
make migrate
```

```bash
make seed
```

Then, each in its own terminal:

```bash
make api
```

```bash
make web
```

```bash
make tunnel
```

Copy the ngrok HTTPS URL into `PUBLIC_BASE_URL`, restart `make api`, then register the webhook:

```bash
make webhook
```

`cd api && uv run bk webhook-info` shows the webhook status and the last delivery error.

Open http://localhost:5173, sign in with `BOSS_EMAIL`, finish setup, then:

1. Settings, Telegram: open the Connect Telegram link on your phone to link yourself as the boss.
2. Settings, Suppliers: create an invite for Ocean Fresh and open it from a second Telegram account.
3. From the supplier account, send an invoice PDF. A clean one posts and you get the FYI. A wrong one arrives as an approval card.

## Demo script

| Step | Who | Send | You see |
| --- | --- | --- | --- |
| 1 | Supplier | Clean invoice PDF | Supplier gets an ack; boss gets "Posted: Ocean Fresh INV-1043, 436.00, due 1 Dec 2026" |
| 2 | Supplier | Invoice with the wrong GST | Boss gets a card explaining the GST difference, with Approve / Edit / Reject |
| 3 | Boss | "how much did I spend on seafood this month?" | One-line answer that matches the P&L on the web |
| 4 | Boss | "sales today 1,850, cash 420, card 1,430" | Proposed entry with the GST split; Confirm posts it |
| 5 | Boss | `/bills`, then Mark paid | Dr Accounts Payable / Cr Bank proposal; Confirm posts it and closes the bill |
| 6 | Boss | `/recap` | Today's invoices, sales, pending approvals, bills due, overdue bills, strangers |
| 7 | Web | Accounting, Journal | Every entry with source and status; click one for lines, checks, the invoice PDF and the audit trail |

## Eval

```bash
make eval
```

Creates a scratch database on the same Postgres server, sends 2 clean invoices and 5 traps (exact duplicate file, wrong total, unknown supplier, price change, prompt injection) through the real webhook and the real Gemini model, prints a table and exits non-zero on any failure. Telegram messages go to a recording fake, so nothing is sent. Samples are built in `api/eval/samples/`; expected outcomes are in `api/eval/expected.toml`.

## Checks

```bash
make verify
```

```bash
make e2e
```

## Repo map

| Path | Purpose |
| --- | --- |
| `planning/` | Brief, PRD, design, tech stack, test spec, decisions, progress |
| `api/src/bookkeeper/ledger/` | Posting service, periods, the ten checks |
| `api/src/bookkeeper/reports/` | Every report number (TB, P&L, BS, cash flow, AP aging, assistant tools, recap) |
| `api/src/bookkeeper/agents/` | Gemini client, extraction, proposals, invoice LangGraph, boss intents |
| `api/src/bookkeeper/telegram/` | Webhook, routing, handlers, keyboards |
| `api/eval/` | Seed data, eval samples, expected outcomes, runner |
| `web/src/` | Vite + React SPA |
