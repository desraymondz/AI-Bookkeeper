Status: Locked (2026-11-18)

# 00 Brief: AI Bookkeeper

## One-line pitch
A Telegram bookkeeper for a small business that logs supplier invoices on its own, keeps proper double-entry books, and only asks the boss when something looks wrong.

## Problem and who has it
- Small F&B owners (example: a Singapore cafe with 3 regular suppliers) get invoices as PDFs and photos in chat apps.
- Logging them, spotting duplicates and price changes, tracking what is due, and producing month-end statements takes hours or an outsourced bookkeeper.
- The owner wants a bookkeeper that behaves like a person in Telegram: quiet when things are normal, asks when they are not, reports on a schedule.

## Reference scenario (seed and demo)
- Business: small cafe, Singapore, SGD, GST configurable.
- Suppliers: seafood, dairy, packaging. Each sends invoices to the bot.
- One boss. Strangers occasionally message the bot.

## Users and roles
| Role | Where | Can do | Cannot do |
| --- | --- | --- | --- |
| Boss | Web (Google sign-in) + Telegram | Everything: view books, settings, users and roles, suppliers, assets, opening balances; approve/edit/reject in Telegram; send sales; ask questions; record manual entries; approve month close | n/a |
| Supplier | Telegram only | Send invoices (PDF/photo), get short acknowledgements | See any books, ask about other suppliers, use the web |
| Stranger | Telegram | Gets one short neutral reply | Anything else; never receives business data |

One deployment = one business (single tenant). Other people clone the repo and run their own.

## Core loop
1. Supplier sends invoice (PDF or photo) to the bot.
2. Agent extracts fields and proposes a journal entry.
3. Deterministic code checks: known supplier, totals add up, GST math, debits = credits, no duplicate, no price change vs history.
4. All checks pass: auto-post to the ledger and send the boss an FYI. Any check fails: boss gets the entry with Approve / Edit / Reject buttons.
5. Boss sends daily sales and marks bills paid; bot reminds about bills due soon.
6. Daily 9pm recap; month-end close prepared by the bot, approved by the boss, then statements PDF sent.

## Success (measurable)
- Eval harness over seeded trap invoices: 100% of traps (duplicate, wrong total, unknown supplier, price change, unbalanced, revised invoice) are held for the boss, 0 are auto-posted.
- 100% of clean seeded invoices auto-post with correct amounts and accounts.
- Trial balance balances after every posting; no unbalanced entry ever reaches the ledger.
- Strangers never receive business data (checked by tests on the reply text and tool access).
- A new person can clone, fill `.env`, run Docker + ngrok, and complete Google sign-in and Telegram linking by following the README.

## Non-goals and cut list
- Multi-business / SaaS tenancy (one deployment per business).
- Asset revaluation (appreciation): Later. Depreciation is in.
- Bank feeds, payment execution, payroll, IRAS GST filing.
- Supplier web access.
- Editing posted entries: corrections are reversals plus new entries.

## Risks and open questions
- Extraction accuracy on blurry photos and handwritten invoices.
- "Any price change goes to boss" may be noisy; threshold stays configurable.
- Excel migration files vary wildly; MVP supports a defined trial-balance layout plus agent mapping with boss approval.
- Gemini model names and pricing change; looked up at stack time.
- Webhook needs public HTTPS: ngrok in dev, reverse proxy on VPS.

## Constraints
- Must-use: Python (uv, ruff, pytest), LangGraph, python-telegram-bot, FastAPI, Postgres in Docker (pgvector-ready), Gemini models, Vite + React SPA + Tailwind + shadcn/ui + Phosphor icons, Montserrat (changed from Next.js after lock, see decisions.md#D-012).
- Hosting: local dev with ngrok tunnel; later any VPS. Files stored in a local folder, metadata in Postgres.
- Budget: hobby scale; prefer cheap Flash-class models where possible.
- Open source friendly: no hardcoded business data, all secrets via `.env`.
