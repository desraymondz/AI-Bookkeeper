# AI Bookkeeper

A Telegram bookkeeper for one small business (the demo is a Singapore cafe). Suppliers send invoices to the bot. The bot reads each one with Gemini, proposes a double-entry journal entry, and runs ten deterministic checks in code. A clean invoice posts on its own and the boss gets a short FYI. Anything that looks wrong waits for the boss with Approve, Edit and Reject buttons. The boss can also ask questions, record cash expenses and sales, mark bills paid and pull a daily recap, all in chat. A read-only web dashboard shows the books.

The model proposes and code decides: nothing posts unless every check passes or the boss approves, and every journal write goes through one ledger posting service that enforces debits = credits, open periods and immutability.

## What works in this prototype

| Area | Built |
| --- | --- |
| Telegram linking | Boss and supplier deep links (`/start <token>`), strangers get a neutral reply and the boss gets Ignore / Add / Block |
| Invoice pipeline | PDF and photo intake, Gemini extraction, 10 checks (known supplier, arithmetic, GST, balanced, duplicate, revision, price change, period, sanity, suspicious content), auto-post with FYI, approval card with Approve / Edit / Reject, bills |
| Boss chat | Questions about spend, sales, bills and balances; "paid 50 cash for ice today"; "sales today 1,850, cash 420, card 1,430"; `/bills` with Mark paid; `/recap` |
| Web | Google sign-in for one boss, settings, chart of accounts, suppliers, users, Telegram connection, opening balances form, Journal with entry detail sheet, Trial balance, P&L, Balance sheet |
| Eval | `bk eval` runs clean and trap invoices through the real pipeline and prints a pass/fail table (11/11 on `gemini-3.5-flash-lite`) |
| Tests | api 461, web 50, Playwright e2e 33, all green under `make verify` and `make e2e` |

Deferred to v1 (see `planning/decisions.md#D-036`): Excel migration, scheduled recap and bill reminders, partial payments and mark paid by text, reversal by chat, fixed assets and depreciation, month-end close and PDF report pack, general ledger, adjusted trial balance and cash flow tabs, analytics, the full 13-trap eval set, production compose profile.

## How it works

```
Supplier (Telegram) ──> webhook ──> role resolved in code (boss / supplier / stranger)
                                         │
                              invoice LangGraph (supplier only)
                                         │
              Gemini extracts fields and proposes a journal entry (JSON schema)
                                         │
                     10 deterministic checks in ledger/ (F-013.1 to .10)
                         │                                   │
                   all pass                            any fail
                         │                                   │
          ledger posting service posts           approval card to the boss
          + template FYI to the boss             (Approve / Edit / Reject)
                                         │
                Postgres (NUMERIC money, immutable posted entries)
                                         │
             reports/ computes every number for the bot and the web
```

- Backend: FastAPI, LangGraph, python-telegram-bot, SQLAlchemy and Alembic on Postgres 18.
- Web: Vite, React, TypeScript, Tailwind 4, shadcn/ui. It reads the books through the API and never edits them.
- LLM: Gemini via one wrapper in `agents/gemini.py`; model IDs come only from env.

## How it was built

Built with Claude Code over one day, spec first.

1. Planning (`/des-plan`): brief, PRD with 31 features and 127 acceptance criteria, design tokens, tech stack and a test spec of 245 rows with fixed expected results, all in `planning/`. Every later change of direction is a dated entry in `planning/decisions.md` (D-001 to D-036).
2. Build (`/des-build`): parallel builder agents in git worktrees, one task per branch, each checked by a blind verifier agent that saw the spec and the diff but not the builder's reasoning. Merges went to `preview` only after `make verify` was green.
3. Guard rails: hooks in `.claude/hooks/` block edits to `.env*` and to test-spec expected results, lint every edited file and run fast tests on stop. `AGENTS.md` holds the hard rules every agent reads.
4. Corrections the agents got wrong and how they were caught are logged in `planning/ai-log.md`. Session handoffs are in `planning/handoffs/`.

## Trade-offs

| Choice | Gain | Cost |
| --- | --- | --- |
| The LLM proposes, code decides (D-019). Ten deterministic checks gate every auto-post. | A wrong extraction or a prompt injection cannot post on its own; the eval shows 0 traps auto-posted. | More invoices go to the boss than a model-trusting design would send. |
| Any unit price change goes to the boss (D-007). | Tight control over supplier pricing. | Noisy for suppliers with variable prices. The rule is configurable in settings. |
| Posted entries are immutable; fixes are reversals (D-018), enforced in the service and by a DB trigger (D-035). | A real audit trail; no silent edits. | Corrections take two entries, and reversal by chat is not built yet. |
| Fixed templates for stranger replies, acks, FYIs and recaps (D-020). | Predictable, cheap, no injection surface on outbound messages. | Less natural wording. |
| Gemini Flash-Lite for every task, set by env (D-016). | Lowest cost; models swap without code changes. | Weaker on messy scans. `bk eval` is the signal for when to upgrade a task. |
| Telegram first, web read-only (D-004). | The boss works where they already are; the web cannot corrupt the books. | Settings and setup still need a laptop. |
| One deployment per business (D-001). | Simple auth, data isolated by default. | No multi-tenant SaaS. |
| Report math only in `reports/` (D-013). | Bot, web and future PDF always show the same numbers. | The web cannot compute anything locally, even a total. |
| Telegram webhook instead of long polling. | Scales with traffic: Telegram pushes updates to a normal HTTP route, so the bot runs behind any web server or load balancer, and dev uses the same code path as production. No rewrite when moving from demo to production. | More setup: it needs a public HTTPS URL, so local runs need an ngrok tunnel and `make webhook` after each URL change. Polling would have worked with no tunnel. |
| Vite + React SPA instead of Next.js (D-012). | One backend (FastAPI) owns auth, data and report math, and the web is a static bundle that can be served from anywhere. New pages and features plug into the same JSON API that the bot uses, so the frontend can grow without moving logic. | No server-side rendering or Next.js conveniences (file routing, server actions). For a signed-in dashboard that is not a real loss. |
| PostgreSQL instead of SQLite. | Built to grow: safe concurrent writes from the webhook, web and background jobs, exact `NUMERIC` money, database triggers for immutability, and pgvector ready for future features such as semantic search over invoices. No database migration later. | Heavier to run: needs Docker for local dev, where SQLite would be a single file. |
| Demo sprint scope cut (D-036): the last four phases were cut to a 6-hour prototype, and per-task verifiers were replaced by one blind verifier at the end. | A working end-to-end demo in time. | Fewer features, and less review per change in the sprint than in phases 1 and 2. |

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
