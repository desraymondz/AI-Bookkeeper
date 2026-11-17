Status: Approved (2026-11-18)

# Build plan: AI Bookkeeper

## Context
Planning docs are locked (31 MVP features, 245 tests). The repo is empty apart from `planning/`, `AGENTS.md`, hooks and `.env.local`. This plan turns the PRD into phased, demoable task cards that Opus builder subagents execute in worktrees, each gated by a blind Opus verifier, merged into `preview`. On approval it is written to `planning/build-plan.md` and the build-order rationale is logged as **D-026**.

Setup answers: builder = Opus, verifier = Opus, browser tests = Playwright, real creds in `.env.local` but no test login.

## Before batch 1 (owner actions)
1. **Start Docker Desktop.** It is down; Postgres and testcontainers integration tests need it.
2. **Playwright**: no Playwright MCP is loaded in this session. Verifiers will use the project's own `@playwright/test` (installed by P1-T02) for walk-throughs and full-page screenshots. Optional MCP: `claude mcp add playwright -- npx @playwright/mcp@latest` then restart the session.
3. **Test login** needs no credentials: it is the code-only bypass `POST /api/test/login` (03-tech-stack.md section 12), active only when `APP_ENV=test` and `E2E_TEST_LOGIN=1`, signing in as `BOSS_EMAIL`. Builders put a dummy `BOSS_EMAIL` in the test config; nothing is read from `.env.local` in tests.
4. Real `.env.local` creds are used only for `bk eval` (P6) and the live Telegram demo.

## Conventions for every card
- Branch `task/<phase>-<id>` off `preview`; parallel tasks get worktree `../AI-Bookkeeper-wt-<id>`.
- **Orchestrator-owned shared files**: `Makefile`, `docker-compose.yml`, `.env.example`, `api/pyproject.toml`, `uv.lock`, `web/package.json`, `pnpm-lock.yaml`, `api/src/bookkeeper/db/models.py`, `api/src/bookkeeper/migrations/`, `api/src/bookkeeper/main.py` (router registration), `web/src/routeTree.gen.ts`, `AGENTS.md`, `planning/*`. P1-T01/T02 create them; later builders request changes in their report.
- Verify (api): `cd api && uv run ruff check . && uv run mypy src tests && uv run pytest <scope>`; (web): `cd web && pnpm check && pnpm typecheck && pnpm test && pnpm build`.
- Integration tests use testcontainers (`pgvector/pgvector:0.8.7-pg18-trixie`); LLM is a fake `LLMClient`; Telegram is a recording fake `Bot`.

## Phases and task cards (compact)

### P1 Foundation. Demo: `make db migrate api web`, test-login to an app shell, settings and chart of accounts, ledger posts balanced entries, demo cafe seeded.
| ID | Task | Features | Tests | Owns | Depends |
|---|---|---|---|---|---|
| P1-T01 | API scaffold: uv project, config (fail-fast env), app factory, db session, all tables from PRD data model + first Alembic migration, testcontainers conftest, `bk` CLI skeleton, Makefile, compose, `.env.example` | F-031.3 | T-232 | `api/` scaffold, root shared files | none |
| P1-T02 | Web scaffold: Vite+React+TS7 (fallback 6.0.3 per D-022), Tailwind 4, shadcn, Phosphor, Montserrat, design tokens light/dark (02-design.md), TanStack Router/Query, Biome, Vitest, Playwright config, app shell + header, empty states | F-029 | T-208 | `web/` | none |
| P1-T03 | Ledger posting service, periods, lock-date move, reversals | G-1, G-2, G-3 | T-001..T-009, T-236 | `ledger/post.py`, `ledger/periods.py`, tests | T01 |
| P1-T04 | Auth: Google OIDC (Authlib), `BOSS_EMAIL` allowlist, server sessions, sign-out, no-store, test-login | F-001 (api) | T-025, T-026, T-029 | `auth/` | T01 |
| P1-T05 | Settings + chart of accounts API, default CoA seed, `/api/config` | F-002, F-003 (api) | T-017, T-035, T-036 (first half), T-038, T-043 | `web_api/settings.py`, `web_api/accounts.py`, `ledger/coa.py` | T01 |
| P1-T06 | Reports service: TB, ATB, GL, P&L, BS, cash flow (indirect), AP aging + read API | G-3, F-025..F-027 (api) | T-009, T-202 | `reports/`, `web_api/reports.py`, `web_api/ledger.py` | T03 |
| P1-T07 | Web: sign-in, access denied, auth guard, first-run setup, settings page, accounts page | F-001..F-003 (web) | T-023, T-024, T-027, T-028, T-030..T-034, T-037, T-039..T-042 | `web/src/features/auth,settings,accounts` + routes | T02, T04, T05 |
| P1-T08 | Seed demo cafe `bk seed` (settings, CoA, 3 suppliers, opening balances, 3 months invoices/sales/payments, 1 asset) | F-030.1 | T-209 | `eval/seed/`, `cli` seed cmd | T03, T05 |

Batches: **B1** T01 ‖ T02 · **B2** T03 ‖ T04 ‖ T05 · **B3** T06 ‖ T07 ‖ T08

### P2 Telegram and invoice pipeline. Demo: supplier sends Ocean Fresh INV-1043 to the bot (fake Telegram in tests, real via ngrok), clean one auto-posts with FYI, trap is held with Approve/Edit/Reject.
| ID | Task | Features | Tests | Depends |
|---|---|---|---|---|
| P2-T01 | Webhook route (secret, update-id dedupe, <2s ack, background), PTB app, sender resolution, `notify` service (boss or sending supplier only), Jinja templates | F-009, G-5 (T-014) | T-078..T-081, T-014 | P1 |
| P2-T02 | Link tokens + boss and supplier linking via `/start`, suppliers and users API | F-006, F-007, F-008 (api/bot) | T-058..T-062, T-064, T-068..T-070, T-075..T-077 | P2-T01 |
| P2-T03 | Stranger handling: template reply, boss card, Ignore/Add/Block, 24h quiet | F-010 | T-082..T-089, T-237, T-238 | P2-T01 |
| P2-T04 | Invoice intake: type/size check, HEIC preview, storage by date/supplier, sha256 dedupe, ack | F-011 | T-090..T-096, T-245 | P2-T01 |
| P2-T05 | Checks F-013.1..F-013.5 (one module each) | F-013 | T-105..T-116, T-125, T-240, T-036 (second half) | P1 |
| P2-T06 | Checks F-013.6..F-013.10 incl. suspicious-content scan | F-013 | T-117..T-124, T-233..T-235, T-239 | P1 |
| P2-T07 | Gemini wrapper (model per env task, retries, audit), extraction schema, propose entry | F-012, G-7 | T-098, T-100..T-104, T-044 | P1 |
| P2-T08 | Invoice LangGraph: checks runner, auto-post + bill + TB guard + FYI, approval card, Approve/Edit/Reject, duplicate and revision cards, boss-only buttons, Postgres checkpointer | F-014, F-015, G-4, G-7 | T-010, T-011, T-018, T-019, T-126, T-127, T-129..T-142, T-241 | T04, T05, T06, T07 |
| P2-T09 | Web: suppliers page + invites, users page, Connect Telegram link + QR | F-006..F-008 (web) | T-057, T-063, T-065..T-067, T-071..T-074 | P2-T02 |

Batches: **B4** T01 ‖ T05 ‖ T06 ‖ T07 · **B5** T02 ‖ T03 ‖ T04 · **B6** T08 ‖ T09

### P3 Boss operations. Demo: boss sends sales, marks a bill paid, asks "how much did I spend on seafood last month", gets 9pm recap.
| ID | Task | Features | Tests | Depends |
|---|---|---|---|---|
| P3-T01 | Boss assistant graph: intent classify, read-only tools over `reports/`, propose tools with Confirm interrupt; Q&A + manual entries + reversal | F-018, F-019 | T-159, T-163..T-166 | P2 |
| P3-T02 | Daily sales (text and Z-report), replace/add, cash+card mismatch | F-016 | T-143, T-145..T-148, T-243 | P3-T01 |
| P3-T03 | Bills, mark paid (button/text), partial payment | F-017.1, .2, .5 | T-150..T-153, T-157 | P3-T01 |
| P3-T04 | Scheduler tick + slot guard + catch-up, bill reminders, daily recap | F-017.3, .4, F-020, F-015.7, F-016.4 | T-140, T-149, T-154..T-156, T-167..T-169 | P2 |
| P3-T05 | Opening balances API + web form (live difference) | F-004 | T-045..T-049 | P1 |
| P3-T06 | Excel trial balance migration via bot | F-005, G-5 (T-013) | T-013, T-050..T-056 | P3-T05, P3-T01 |

Batches: **B7** T01 ‖ T04 ‖ T05 · **B8** T02 ‖ T03 ‖ T06

### P4 Month end. Demo: Oct close prepared on 1 Nov, boss approves, period locks, PDF pack arrives.
| ID | Task | Features | Tests | Depends |
|---|---|---|---|---|
| P4-T01 | Assets API + web, depreciation schedule | F-021 | T-170..T-174, T-242 | P1 |
| P4-T02 | Month-end close prep, checklist, approve, lock | F-022 | T-175..T-179, T-244 | P4-T01, P3-T04 |
| P4-T03 | PDF report pack (WeasyPrint) + headline message | F-023 | T-180..T-182 | P4-T02 |
Batches: **B9** T01 · **B10** T02 · **B11** T03

### P5 Web books. Demo: every accounting tab and analytics on seeded data, numbers match bot and PDF. (Can start once P1 is merged; runs alongside P3/P4 if context allows.)
| ID | Task | Features | Tests | Depends |
|---|---|---|---|---|
| P5-T01 | Journal tab, date range filter, entry detail sheet (lines, checks, document viewer, audit, reversal link), G-8 read-only | F-024, G-6, G-8 | T-016, T-020..T-022, T-183..T-191 | P1-T06 |
| P5-T02 | General ledger tab | F-025 | T-192..T-194 | P5-T01 (filter component) |
| P5-T03 | TB / ATB tabs | F-026 | T-195..T-198 | P5-T01 |
| P5-T04 | P&L, BS, cash flow tabs | F-027 | T-199..T-201 | P5-T01 |
| P5-T05 | Analytics page (charts + API) | F-028 | T-203..T-207 | P5-T01 |
Batches: **B12** T01 · **B13** T02 ‖ T03 ‖ T04 ‖ T05

### P6 Eval and self-host. Demo: `bk eval` table all green against real Gemini; fresh clone runs from README.
| ID | Task | Features | Tests | Depends |
|---|---|---|---|---|
| P6-T01 | Clean + trap samples (13 traps), `expected.yaml`, eval runner (real pipeline, table, exit code) | F-030.2..4, plus eval rows | T-097, T-099, T-128, T-144, T-158, T-160..T-162, T-210..T-229 | all |
| P6-T02 | README credentials checklist, compose prod profile, Caddy, ngrok script, `bk set-webhook` | F-031.1, .2 | T-230, T-231 | all |
Batches: **B14** T01 ‖ T02, then `make eval` with real creds (only step that reads `.env.local`, run by you or me on your OK).

## Dependency rationale (goes into D-026)
Scaffolds first because they create all shared files; ledger and reports next because every write path (G-1) and every number (bot, web, PDF must match) depends on them; deterministic checks and the extractor are independent leaf modules so they run in parallel before the invoice graph that wires them; web books come after the reports service so pages only render, never compute.

## Hooks audit
Present and fine: lint-on-edit, block `.env*` edits/reads, test-spec only `[ ]`->`[x]`, quick unit tests on Stop, deny force push and `git push origin main`.
Gaps to add after approval (in `.claude/settings.json`):
- Add denies `Bash(git push origin HEAD:main*)` and `Bash(git push -u origin main*)` (current deny only matches `git push origin main`). Main changes only via the final PR.
- Lint-on-edit hook matches only paths under the main checkout, so worktree edits are not linted on save; builders' Verify command covers it. No change needed, noted.

## Orchestrator steps
1. Write `planning/build-plan.md` (full cards with Owns/Reads/Verify/UI change lines), add D-026, add hook denies.
2. `git checkout -b preview main`; commit plan + D-026 on `preview`.
3. Launch B1: P1-T01 and P1-T02 in worktrees, Opus builders in background. Verify each with a fresh Opus verifier; merge on PASS; tick T-xxx; update `progress.md`.
4. Continue batch by batch; handoff (`des-handoff`) at each phase end.

## Verification
Per task: blind verifier runs lint, typecheck, tests, build and Playwright walk-through with before/after screenshots in `planning/evidence/<task-id>/`. Per phase: full suite on `preview` plus regression verifier. Final: `make lint typecheck test e2e build`, `make eval` with real Gemini, PR `preview -> main` left for your merge.

## Card defaults
Unless a card says otherwise: Reads = `AGENTS.md`, the PRD sections of its features, `03-tech-stack.md` sections 3, 5, 9, 12, `decisions.md` entries named in the PRD section; UI cards also read `02-design.md`. Verify = the api and/or web command from Conventions scoped to the card's tests. UI change = yes for any card owning `web/` files. Full cards for later phases are written at the start of each phase.

## P1 full cards

### P1-T01  API scaffold
Feature: F-031.3     Tests: T-232
Owns files: api/** (pyproject.toml, uv.lock, alembic.ini, src/bookkeeper/{main,config,cli}.py, db/, migrations/, tests/conftest.py), Makefile, docker-compose.yml, .env.example, storage/.gitkeep
Reads: planning/01-prd.md#data-model-sketch, 03-tech-stack.md sections 3, 9, 10, 11, 12
Depends on: none
Verify: cd api && uv sync && uv run ruff check . && uv run mypy src tests && uv run pytest && uv run alembic upgrade head (against compose db)
UI change: no

### P1-T02  Web scaffold and app shell
Feature: F-029.1     Tests: T-208
Owns files: web/**
Reads: planning/02-design.md (all), 03-tech-stack.md section 8, 9, 10.2
Depends on: none
Verify: cd web && pnpm install && pnpm check && pnpm typecheck && pnpm test && pnpm build
UI change: yes

### P1-T03  Ledger posting service and periods
Feature: G-1, G-2, G-3     Tests: T-001 to T-009, T-236
Owns files: api/src/bookkeeper/ledger/{post,periods,money}.py, api/tests/unit/ledger/, api/tests/integration/ledger/
Reads: 01-prd.md#global-rules, decisions.md#D-018, #D-024
Depends on: P1-T01
Verify: api command, pytest tests/unit/ledger tests/integration/ledger
UI change: no

### P1-T04  Auth API
Feature: F-001 (api)     Tests: T-025, T-026, T-029
Owns files: api/src/bookkeeper/auth/, api/tests/**/auth/
Reads: 01-prd.md#F-001, decisions.md#D-013, 03-tech-stack.md section 3.2 (Authlib, itsdangerous), 12 (test login)
Depends on: P1-T01
Verify: api command, pytest -k auth
UI change: no

### P1-T05  Settings and chart of accounts API
Feature: F-002, F-003 (api), plus GET /api/config per D-027     Tests: T-017, T-035, T-036 (posted entry unchanged; the 8% check half ticks in P2-T05), T-038, T-043
Owns files: api/src/bookkeeper/web_api/{settings,accounts,config}.py, api/src/bookkeeper/ledger/coa.py, tests
Reads: 01-prd.md#F-002, #F-003, decisions.md#D-004
Depends on: P1-T01
Verify: api command
UI change: no

### P1-T06  Reports service and read API
Feature: F-025 to F-027 (api), G-3     Tests: T-009, T-202
Owns files: api/src/bookkeeper/reports/, api/src/bookkeeper/web_api/{reports,ledger}.py, tests
Depends on: P1-T03
Verify: api command
UI change: no

### P1-T07  Web auth, setup, settings, accounts
Feature: F-001 to F-003 (web)     Tests: T-023, T-024, T-027, T-028, T-030 to T-034, T-037, T-039 to T-042
Owns files: web/src/features/{auth,settings,accounts}/, web/src/routes/{sign-in,access-denied,setup,settings}*, web/e2e/{auth,settings,accounts}.spec.ts
Depends on: P1-T02, P1-T04, P1-T05
Verify: web command plus pnpm e2e for its specs
UI change: yes

### P1-T08  Demo cafe seed
Feature: F-030.1     Tests: T-209
Owns files: api/eval/seed/, api/src/bookkeeper/cli.py seed command (orchestrator applies if conflicting), tests
Depends on: P1-T03, P1-T05
Verify: api command, uv run bk seed on a fresh db
UI change: no

## Verifier notes carried forward
- P1-T03: request a migration changing `journal_lines` and `check_results` FKs from `ondelete=CASCADE` to `RESTRICT` (DB-level guard for G-2). Orchestrator applies it to models.py and migrations.
- P4-T01: depreciation entries need an `asset_id` link on journal entries for per-asset accumulated depreciation (F-021.3); request schema change.
- Auth wiring: feature routers are plain `APIRouter`s; `main.py` (orchestrator) registers them with `dependencies=[Depends(require_boss)]` from `bookkeeper.auth.deps`. Public routes: `/api/auth/*`, `/api/config`, `/api/test/login` (test env), `/telegram/webhook`. P1-T04 adds a test that walks `app.routes` and asserts 401 for every non-public route (T-026), so later routers are covered automatically.
- T-005 (all write paths) and T-011 tick only when the last write path (P4-T02 depreciation) is merged; P1-T03 proves the service-level guarantee.
