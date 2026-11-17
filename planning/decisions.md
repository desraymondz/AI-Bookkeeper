# Decisions

Format: date, context, decision, rejected, why, affects. Locked docs change only through a new entry here.

## D-001 One deployment per business
- Date: 2026-11-18
- Context: Repo should be cloneable by other owners.
- Decision: Single tenant. Each business clones and runs its own deployment.
- Rejected: Multi-tenant SaaS (F-202, Later).
- Why: Simpler auth, data isolation by default, matches self-host goal.
- Affects: 00-brief.md#users-and-roles, 01-prd.md F-031

## D-002 Revenue comes from boss daily sales in Telegram
- Date: 2026-11-18
- Context: P&L, cash flow and margins need revenue; brief only covered supplier invoices.
- Decision: Boss sends daily sales (text or Z-report photo); bot proposes, boss confirms.
- Rejected: Seed-only revenue; CSV upload on web; expenses-only MVP.
- Why: Keeps everything in Telegram and makes statements real.
- Affects: 01-prd.md F-016

## D-003 Accrual books with payables, boss marks paid, bot reminds
- Date: 2026-11-18
- Context: Invoices are bills payable later.
- Decision: Dr Expense / Cr AP on receipt; boss marks paid (button or text) to post Dr AP / Cr Bank; reminders before and on due date.
- Rejected: Paid on receipt; auto-paid on due date.
- Why: Real accrual books, AP aging, and the user wants the bot to be a good reminder.
- Affects: 01-prd.md F-017

## D-004 Web holds business settings; books stay read-only
- Date: 2026-11-18
- Context: GST status differs per business; user wants web as the config for business needs.
- Decision: GST on/off and rate, price rule, report times, etc. are edited on the web settings page. Books cannot be edited on the web (G-8).
- Rejected: Env-only config; hard-coded GST.
- Why: Cloners configure without code; verification UI stays trustworthy.
- Affects: 01-prd.md G-8, F-002

## D-005 Strangers get a short neutral reply and the boss is asked
- Date: 2026-11-18
- Context: User notes conflicted between silence and a short human reply.
- Decision: One short neutral reply, no business data; boss gets Ignore / Add as supplier / Block. No repeat for 24 h.
- Rejected: Silent + ask boss; silent with no ping.
- Why: Human-like, safe, and keeps the boss in control.
- Affects: 01-prd.md F-010

## D-006 Fixed assets registered on web; depreciation at month end; no revaluation in MVP
- Date: 2026-11-18
- Context: Depreciation needs an asset register. User mentioned appreciation.
- Decision: Web asset form, straight-line, adjusting entries at month-end close. Revaluation moved to Later (F-201).
- Rejected: Bot detects capital items; seed-only assets.
- Why: Rare for a small cafe; depreciation covers the accounting cycle.
- Affects: 01-prd.md F-021, F-022

## D-007 Any unit price change goes to the boss
- Date: 2026-11-18
- Context: Price spike threshold.
- Decision: Default rule is any unit price change vs last price for the same item from that supplier; rule is configurable in settings.
- Rejected: +20% vs 90-day average; +10% vs last invoice.
- Why: User preference; tighter control for MVP.
- Affects: 01-prd.md F-013.7, F-002.2

## D-008 Daily 9pm text recap, monthly PDF pack
- Date: 2026-11-18
- Decision: Daily recap at 21:00 business time; on the 1st, close prep then PDF statements after approval. Times configurable.
- Rejected: Text-only monthly; monthly only.
- Affects: 01-prd.md F-020, F-022, F-023

## D-009 Opening balances by web form and by Excel upload to the bot, both MVP
- Date: 2026-11-18
- Decision: Web opening balance form (F-004) and Excel trial balance migration via Telegram (F-005), both requiring balance and boss approval.
- Rejected: Excel in v1 only; config file.
- Why: User wants migration to be as simple as uploading their Excel.
- Affects: 01-prd.md F-004, F-005

## D-010 Boss chat covers Q&A and manual entries with Confirm
- Date: 2026-11-18
- Decision: Read-only ledger Q&A plus manual entries and reversals, nothing posts without Confirm.
- Rejected: Q&A only; commands only.
- Affects: 01-prd.md F-018, F-019

## D-011 Boss approves month close; periods lock
- Date: 2026-11-18
- Decision: Bot prepares adjusting entries and checks; boss taps Approve close; period locks; no unlock in MVP.
- Rejected: Auto-post and lock; never lock.
- Affects: 01-prd.md G-3, F-022

## D-012 Vite + React SPA replaces Next.js; Vitest for web tests
- Date: 2026-11-18
- Context: Brief (locked) named Next.js. User asked to replan with Vite and Vitest during stack phase.
- Decision: Vite + React + TypeScript SPA, pnpm, Vitest; brief constraint line updated with a pointer here.
- Rejected: Next.js.
- Why: User preference; with FastAPI as the only backend, SSR adds nothing.
- Affects: 00-brief.md#constraints, 03-tech-stack.md section 8

## D-013 FastAPI is the only backend and owns Google sign-in
- Date: 2026-11-18
- Decision: FastAPI serves webhook, JSON API, Google OAuth (server side, httpOnly session cookie, `BOSS_EMAIL` allowlist), and document files. Vite dev server proxies `/api`.
- Rejected: Web reading Postgres directly; Auth.js in a Next server.
- Why: Accounting math lives once in Python, so bot, PDF and web numbers always match (F-023.3, F-028.4).
- Affects: 03-tech-stack.md sections 1, 3

## D-014 Full docker compose for cloners, Caddy for HTTPS
- Date: 2026-11-18
- Decision: Compose with Postgres always on; api, web, caddy under a `prod` profile. Dev runs api and web natively plus ngrok.
- Rejected: Postgres-only Docker everywhere.
- Affects: 03-tech-stack.md sections 9, 10

## D-015 pnpm for the web
- Date: 2026-11-18
- Rejected: npm, bun.
- Affects: 03-tech-stack.md section 8

## D-016 Every LLM task uses gemini-3.5-flash-lite by default; models set by env
- Date: 2026-11-18
- Context: Stack draft proposed gemini-4-hydrogen for heavier tasks. User wants cheapest model first and models to be swappable because they get deprecated.
- Decision: One env var per task, all default `gemini-3.5-flash-lite`, escalation disabled. Upgrade a task only when `bk eval` shows failures; first candidate `gemini-4-hydrogen`. No model IDs hard-coded outside settings defaults.
- Rejected: Mixed Hydrogen / Flash-Lite / Argon defaults.
- Why: Cost, and the eval harness gives an objective upgrade signal.
- Affects: 03-tech-stack.md section 4, section 11

## D-017 Light and dark themes following the system
- Date: 2026-11-18
- Decision: Black and white tokens with an inverse dark theme; toggle System / Light / Dark.
- Rejected: Light only.
- Affects: 02-design.md tokens

## D-018 Posted entries are immutable; corrections are reversals
- Date: 2026-11-18
- Context: Revised invoices and mistakes must be fixable.
- Decision: Never edit or delete a posted entry; post a linked reversal plus a new entry.
- Rejected: In-place edits.
- Why: Audit trail; boss can verify every change.
- Affects: 01-prd.md G-2, F-015.6, F-019.3

## D-019 The LLM proposes, code decides
- Date: 2026-11-18
- Decision: Extraction and proposals come from the LLM; posting is gated by deterministic checks (F-013) or boss approval. No LLM-generated SQL.
- Why: Determinism and safety for money.
- Affects: 01-prd.md G-4, F-013

## D-020 Fixed templates, not the LLM, for stranger replies, acks, FYIs, recaps, reminders
- Date: 2026-11-18
- Decision: Jinja2 templates for these messages.
- Why: Zero leak risk to strangers, zero cost, testable text.
- Affects: 03-tech-stack.md section 4, 01-prd.md F-010.1

## D-021 Analytics core set in MVP
- Date: 2026-11-18
- Decision: Revenue / expenses / net profit bars, three margin lines, spend by supplier, top cost accounts. Other ideas listed as F-101.
- Rejected: Defer page; full set now.
- Affects: 01-prd.md F-028, F-101

## D-022 Biome over ESLint + Prettier; TypeScript 7
- Date: 2026-11-18
- Context: typescript-eslint did not support TS 7 at lookup time.
- Decision: Biome for lint and format; TS 7. Fallback if shadcn breaks: TS 6.0.3.
- Rejected: ESLint + Prettier with TS 6.
- Affects: 03-tech-stack.md section 8

## D-023 Backend library picks
- Date: 2026-11-18
- Decision: mypy (pydantic plugin) over pyright; APScheduler 3.x (4.0 is alpha) with a DB run-once guard; WeasyPrint for PDF; TanStack Router for typed URL search params (date filters); Recharts via shadcn charts; Makefile at root.
- Affects: 03-tech-stack.md sections 3, 6, 8, 10

## D-024 Defaults for gaps found by the blind test spec
- Date: 2026-11-18
- Context: Test-spec author flagged under-specified PRD criteria.
- Decision:
  - Late item for a locked period posts on the first day of the first open period, with a note naming the original date (G-3, F-013.8).
  - A pending stranger who messages again gets no reply and no new boss card until the boss decides; pending strangers are listed in the daily recap. Stranger files are not stored (F-010.4, F-010.5).
  - Same supplier + invoice number with different amounts is a Revision, not a Duplicate. The duplicate window is measured on invoice date (F-013.5, F-013.6).
  - After a rollback for TB imbalance the entry is `pending_approval` with a failed check naming the imbalance (F-014.3).
  - Depreciation is rounded to cents monthly; the final month absorbs the remainder (F-021.2).
  - If cash + card does not equal the sales total, the bot asks the boss and posts nothing (F-016.2).
  - Missing sales days are listed at close but do not block it (F-022.2).
  - Oversize file reply: too big, send under 20 MB (F-011.1).
- Why: Testable defaults; boss stays in control on anything ambiguous.
- Affects: 04-test-spec.md T-236 to T-245

## D-025 Add check F-013.10 Suspicious content
- Date: 2026-11-18
- Context: The prompt-injection trap (F-030.2) has clean numbers and would pass F-013.1 to F-013.9, breaking "0 traps auto-posted" (F-030.4).
- Decision: New deterministic check. Fails if a code pattern scan finds instruction-like text in the document or the extractor flags it. Added to the locked PRD with a pointer here.
- Rejected: Changing the eval so the trap passes when the injected text has no effect.
- Why: Defence in depth; an injected document should always be seen by the boss.
- Affects: 01-prd.md F-013.10, 04-test-spec.md T-222, T-233 to T-235

## D-026 Build order
- Date: 2026-11-18
- Context: des-build needs a dependency-safe order for parallel builders.
- Decision: Six phases (foundation, Telegram and invoice pipeline, boss operations, month end, web books, eval and self-host) per `planning/build-plan.md`. Scaffolds first because they create all shared files; ledger and reports next because every write path (G-1) and every number shown by bot, web and PDF depends on them; checks and extractor are independent leaf modules built in parallel before the invoice graph wires them; web books follow the reports service so pages only render, never compute. Builder and verifier both run on Opus; browser checks use the project's Playwright with the test-only login.
- Rejected: Feature-by-feature vertical slices from the start (would race on the schema and shared files).
- Why: Fewer merge conflicts, earliest possible trust in the ledger.
- Affects: planning/build-plan.md

## D-027 Montserrat self-hosted; /api/config contract
- Date: 2026-11-18
- Context: 02-design.md section 4 links Google Fonts; 03-tech-stack.md section 8 picks @fontsource-variable/montserrat. The web shell needs the bot username and business name before sign-in data loads.
- Decision: Self-host Montserrat via @fontsource-variable (tech stack wins; no external font request). API exposes `GET /api/config` returning `{ bot_username, business_name }` (both nullable), built in P1-T05.
- Rejected: Google Fonts CDN; `VITE_` env var for the bot username (would need a rebuild per deployment).
- Affects: 02-design.md section 4, 03-tech-stack.md section 8, planning/build-plan.md P1-T05

## D-028 tenacity pinned to 9.1.x
- Date: 2026-11-18
- Context: 03-tech-stack.md section 3.2 pins tenacity 9.2.1, but google-genai 3.4.0 requires tenacity<9.2.0.
- Decision: Pin `tenacity~=9.1.4` until google-genai relaxes the bound.
- Rejected: Downgrading google-genai.
- Affects: 03-tech-stack.md section 3.2, api/pyproject.toml

## D-029 Price-change rule options
- Date: 2026-11-18
- Context: D-007 makes the price rule configurable but names only the default. The settings builder added a second value.
- Decision: `price_rule` accepts `any_change` (default, D-007) and `increase_only` (only unit price increases go to the boss). F-013.7 applies whichever is set.
- Rejected: A percentage threshold (left for later if the default proves noisy).
- Affects: 01-prd.md F-002.2, F-013.7; api/src/bookkeeper/settings_service.py

## D-030 Report definitions not fixed by the PRD
- Date: 2026-11-18
- Context: P1-T06 had to choose meanings the PRD leaves open; the verifier asked for them to be recorded.
- Decision:
  - Date presets (F-024.2), in business timezone: This month = 1st to today; Last month = whole previous month; Last 3 months and Last 12 months = from the 1st of the month 2 (or 11) months back to today, current month included; Year to date = from the latest `fy_start_month` 1st to today; default = This month.
  - Packaging is COGS (subtype `cogs`), so gross margin is after packaging.
  - P&L and cash flow exclude closing entries; the balance sheet shows unclosed earnings as "Current period earnings" in equity.
  - AP aging buckets by days past due date; "current" includes bills not yet due.
- Rejected: Rolling 30/90/365-day windows (harder to compare month to month).
- Open: cash flow finds payables by the word "payable" in the account name; move to a subtype rule before boss-added liability accounts matter (carry forward to P2-T02).
- Affects: 01-prd.md F-024.2, F-027, F-023.1; api/src/bookkeeper/reports/
