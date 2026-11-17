Status: Locked (2026-11-18)

# 03 Tech Stack: AI Bookkeeper

Decisions: `planning/decisions.md` (D-012 to D-016, D-019, D-020, D-022, D-023).

Sources: `planning/00-brief.md`, `planning/01-prd.md`. Feature IDs (F-xxx, G-x) refer to the PRD.

Versions, Gemini model IDs and prices were looked up on 2026-11-18 from PyPI, the npm registry, Docker Hub, endoflife.date, GitHub releases, ai.google.dev (now redirects to aistudio.google.com/docs) and ui.shadcn.com. Pin with `~=` (Python) or `^` (npm) at these versions, commit lockfiles (`uv.lock`, `pnpm-lock.yaml`), and re-check before the first build.

## 1. Architecture at a glance

```
Telegram ──HTTPS──> Caddy ──/telegram/webhook──> FastAPI (api) ──> Postgres 18 + pgvector
Browser  ──HTTPS──> Caddy ──/api/*──────────────> FastAPI (api) ──> storage/ (invoice files)
                          └─ everything else ──> web (static Vite build)
FastAPI process also hosts: python-telegram-bot Application, LangGraph graphs, APScheduler, Gemini calls.
```

- One backend: FastAPI serves the Telegram webhook, the JSON API for the web, Google OAuth sign-in, and document file downloads (boss only).
- One API process (single replica). Scheduler and background tasks run in-process; idempotency is enforced in Postgres so restarts and accidental double processes stay safe.
- Same origin everywhere: in dev Vite proxies `/api` to FastAPI; in prod Caddy routes `/api` and `/telegram` to FastAPI and the rest to the web container. Cookies are first-party and `SameSite=Lax`.

## 2. Runtimes and base images

| Tool | Version | Why it fits | Rejected alternatives |
| --- | --- | --- | --- |
| Python | 3.14 (3.14.10) | Supported to 2030; all chosen libs ship wheels for it | 3.15: released 2026-10, wheel coverage (WeasyPrint deps, pillow-heif, psycopg-binary) still catching up. 3.12/3.13: no benefit, shorter support |
| Node.js | 26 LTS (26.13.1) | Active LTS since 2026-10-28; satisfies Vite 8 (`>=22.12`) and pnpm 12 | 24 LTS: works, but older; 25: EOL |
| Postgres image | `pgvector/pgvector:0.8.7-pg18-trixie` | Postgres 18.7 with pgvector 0.8.7 preinstalled, ready for F-105 | Plain `postgres:18`: needs extension build later. Supabase/Neon: external service, breaks self-host promise (F-031) |
| Caddy | 2.11.9 (`caddy:2.11`) | Automatic HTTPS for the domain, tiny config, also serves the SPA static files | Nginx + certbot: more moving parts. Traefik: heavier config for one host |
| Python image | `python:3.14-slim-trixie` + `ghcr.io/astral-sh/uv:0.13.9` (copy binary) | Matches dev Python; Debian trixie has Pango for WeasyPrint | Alpine: musl wheels and Pango pain |

## 3. Backend (Python, `api/`)

### 3.1 Tooling

| Tool | Version | Why it fits | Rejected alternatives |
| --- | --- | --- | --- |
| uv | 0.13.9 | Env + deps + lockfile + Python install in one fast tool (brief constraint) | Poetry, pip-tools: slower, separate Python management |
| ruff | 0.17.5 | Lint and format in one binary (`ruff check`, `ruff format`) | Black + flake8 + isort: three tools for the same job |
| mypy | 2.4.1 | Pure Python, installs via uv with no Node runtime; strict mode; official pydantic plugin; SQLAlchemy 2 `Mapped[...]` types work natively. Money and ledger code benefit from strict `Decimal` typing (G-1) | pyright 1.1.414: excellent, but the PyPI package downloads a Node runtime at first run (friction in Docker/CI). basedpyright 1.40.2: same Node dependency. ty 0.0.105: still Beta |
| pytest | 9.2.0 | Standard runner, markers for unit vs integration | unittest: verbose, weaker fixtures |
| pytest-asyncio | 1.5.0 | Async FastAPI, PTB and SQLAlchemy code under test | anyio plugin only: fine, but pytest-asyncio is the common default for these libs |
| hypothesis | 6.170.15 | Property tests for G-1 (random balanced/unbalanced entries), GST rounding, depreciation | Hand-written cases only: misses edge cases in money math |
| testcontainers | 4.15.0 | Spins a real pgvector Postgres per test session for integration tests | SQLite: different SQL, no JSONB/NUMERIC semantics, would hide bugs |
| time-machine | 3.6.0 | Freeze time for scheduler slots, due dates, period locks (F-017, F-020, F-022) | freezegun 1.5.5: slower, less maintained |
| pytest-cov | 7.1.0 | Coverage report for ledger and checks modules | n/a |

### 3.2 Runtime libraries

| Tool | Version | Why it fits (PRD) | Rejected alternatives |
| --- | --- | --- | --- |
| FastAPI | 0.163.1 | Only backend: webhook (F-009), JSON API (F-002 to F-008, F-024 to F-028), OAuth (F-001), file serving (F-024.3). Pydantic models shared with LLM schemas | Django: ORM and admin not needed, heavier. Separate Node BFF: user decided FastAPI owns auth |
| Uvicorn | 0.54.0 | ASGI server, `--reload` in dev | Hypercorn, Granian: no need |
| pydantic | 2.14.3 | Request/response models and LLM structured output schemas (F-012.2) | attrs/marshmallow: no Gemini schema integration |
| pydantic-settings | 2.16.3 | Typed `.env` loading; startup fails with a list of missing vars (F-031.3) | python-dotenv alone: no validation |
| Authlib | 1.9.8 | Google OpenID Connect via `authlib.integrations.starlette_client`; verifies ID token, then email checked against `BOSS_EMAIL` (F-001.1) | fastapi-users: brings user DB model we do not want. Hand-rolled OAuth: easy to get state/nonce wrong |
| itsdangerous | 2.2.0 | Signs the session cookie (Starlette `SessionMiddleware`), httpOnly, `Secure` in prod, `SameSite=Lax`. Cookie stores a session id that maps to a `web_sessions` row so sign-out revokes server-side (F-001.3). API responses send `Cache-Control: no-store` | JWT in localStorage: XSS-exposed, hard to revoke |
| python-telegram-bot | 22.8 | Webhook mode with `Application.builder().updater(None)`; FastAPI route verifies `X-Telegram-Bot-Api-Secret-Token`, calls `application.process_update` in a background task. Inline keyboards for Approve/Edit/Reject (F-015), deep links `?start=<token>` (F-006, F-007) | aiogram: fine, but user chose PTB. Polling: needs no HTTPS but cannot scale to prod webhook flow |
| LangGraph | 1.2.22 | Stateful graphs with `interrupt()` / `Command(resume=...)` for boss approval paused across days (F-015, F-016, F-019) | Plain function calls: no durable pause/resume. CrewAI, LlamaIndex agents: weaker control over deterministic nodes |
| langgraph-checkpoint-postgres | 3.2.1 | `AsyncPostgresSaver` on psycopg 3; checkpoints live in the same Postgres | SQLite/Memory saver: lost on restart, not shared with prod DB |
| google-genai | 3.4.0 | Official Google Gen AI Python SDK (`from google import genai`); `client.aio.models.generate_content` with `response_schema` = Pydantic model, inline PDF/image parts, function calling | `google-generativeai`: legacy SDK. `langchain-google-genai` 4.5.0: extra abstraction; LangGraph nodes call the SDK directly so model, tokens and errors are logged exactly (G-7) |
| SQLAlchemy | 2.1.9 | Typed ORM (`Mapped[Decimal]`), async engine, `Numeric(14, 2)` for money, `JSONB` for `extraction_json` and audit `detail_json` | SQLModel: thin layer, lags SQLAlchemy releases. Raw SQL: no migrations autogen |
| Alembic | 1.20.1 | Migrations, autogenerate from models; `alembic upgrade head` in container start | Manual SQL files: easy to drift |
| psycopg (+ `binary`, `pool`) | 3.3.9 (pool 3.3.3) | One driver for SQLAlchemy async and the LangGraph checkpointer | asyncpg 0.32.0: fast, but the LangGraph Postgres saver needs psycopg anyway; one driver is simpler |
| pgvector (Python) | 0.5.1 | SQLAlchemy `Vector` type for F-105 later; install now, unused in MVP | n/a |
| APScheduler | 3.11.3 | In-process `AsyncIOScheduler` (see section 6) | APScheduler 4.0.0a6: still alpha. Celery beat / arq: need Redis. Host cron: second process and still needs a guard |
| WeasyPrint | 70.0 | Monthly PDF pack (F-023) from Jinja2 HTML + CSS: tables, page breaks, headers, Montserrat font; same numbers as web because both read the same report service (F-023.3) | ReportLab 5.1.0: precise but low-level canvas code for every table. Headless Chrome: heavy image |
| Jinja2 | 3.1.6 | Templates for the PDF and message templates | n/a |
| openpyxl | 3.1.5 | Reads first sheet of `.xlsx` trial balance (F-005), `read_only=True, data_only=True` | pandas: large dependency for one sheet |
| Pillow + pillow-heif | 13.0.0 + 1.8.1 | Decode HEIC (F-011.1), make a JPEG preview for the browser (browsers do not show HEIC), normalize orientation before extraction | n/a |
| rapidfuzz | 3.14.6 | Fuzzy supplier name match (F-013.1), item normalization for price change (F-013.7), Excel row to account pre-match (F-005.2) | LLM for matching: non-deterministic, violates G-4 |
| tenacity | 9.2.1 | "Retry twice then send to boss as could not read" for LLM calls (NFR Reliability) | Hand-rolled loops |
| structlog | 26.1.0 | JSON logs with update_id, thread_id, model; complements DB audit log (G-7) | stdlib logging only: no structured context |
| httpx | 0.28.1 | Test client for FastAPI; used by PTB internally | requests: sync only |

## 4. LLM: Gemini model per task

Prices: Gemini API Standard paid tier, USD per 1M tokens, output includes thinking tokens, as published on 2026-11-18. Free tier exists for Hydrogen and the Flash/Flash-Lite models below (useful for dev and eval), not for Argon/Carbon.

| Model ID | Class | Input / Output per 1M | Inputs | Notes |
| --- | --- | --- | --- | --- |
| `gemini-4-hydrogen` | Fast tier (successor to 3.8 Flash, launched 2026-11-12) | $1.50 / $7.50 | Text, image, PDF, audio, video | Stable; structured output, function calling, thinking levels low/medium/high/xhigh |
| `gemini-3.5-flash-lite` | Flash-Lite | $0.30 / $2.50 | Text, image, PDF, audio, video | Stable; structured output, function calling, thinking |
| `gemini-3.1-flash-lite` | Flash-Lite (older) | $0.25 / $1.50 | Text, image, video, (audio $0.50) | Stable; cheapest current-gen fallback |
| `gemini-3.8-flash` | Flash (previous gen) | $0.75 / $3.75 until 2026-12-31, then $1.50 / $7.50 | Multimodal | Same price as Hydrogen from 2027, so not chosen |
| `gemini-4-argon` | Frontier reasoning (Pro class) | $2.00 / $10.00 until 2026-11-30, then $4.00 / $20.00 | Text, image, PDF, audio, video | No free tier; used only for escalation |
| `gemini-4-carbon` | Strongest reasoning | Same as Argon | Same | Not used: overkill for bookkeeping |

Model per task. Every task reads its own env var, so swapping or upgrading a model needs no code change (see decisions.md#D-016). MVP default: `gemini-3.5-flash-lite` for every LLM task. Upgrade a task only when the eval harness (F-030) shows it failing; first upgrade candidate is `gemini-4-hydrogen` for extraction and the boss agent.

| Task | Graph / node | Env var | MVP default | Upgrade candidate | Thinking |
| --- | --- | --- | --- | --- | --- |
| Invoice extraction from PDF/photo (F-012) | invoice / `extract` | `GEMINI_MODEL_EXTRACT` | `gemini-3.5-flash-lite` | `gemini-4-hydrogen` | low |
| Extraction escalation (schema fails twice, F-012.2) | invoice / `extract_retry` | `GEMINI_MODEL_EXTRACT_ESCALATE` | empty (disabled) | `gemini-4-hydrogen` or `gemini-4-argon` | medium |
| Edit-instruction revision (F-015.3) | invoice / `revise` | `GEMINI_MODEL_REVISE` | `gemini-3.5-flash-lite` | `gemini-4-hydrogen` | low |
| Excel trial-balance mapping (F-005) | assistant / `map_excel` | `GEMINI_MODEL_EXCEL_MAP` | `gemini-3.5-flash-lite` | `gemini-4-hydrogen` | low |
| Boss Q&A with read-only ledger tools (F-018) | assistant / `agent` | `GEMINI_MODEL_ASSISTANT` | `gemini-3.5-flash-lite` | `gemini-4-hydrogen` | low |
| Manual entry and payment proposals (F-017.2, F-019) | assistant / `agent` (propose tools) | `GEMINI_MODEL_ASSISTANT` | `gemini-3.5-flash-lite` | `gemini-4-hydrogen` | low |
| Daily sales parsing, text or Z-report photo (F-016) | assistant / `parse_sales` | `GEMINI_MODEL_SALES` | `gemini-3.5-flash-lite` | n/a | off |
| Intent classification of boss free text | router / `classify_intent` | `GEMINI_MODEL_ROUTER` | `gemini-3.5-flash-lite` | n/a | off |
| Short conversational replies (F-015.4, F-018.4) | various / `write_reply` | `GEMINI_MODEL_REPLY` | `gemini-3.5-flash-lite` | n/a | off |
| Stranger reply, supplier ack, FYI, recap, reminders (F-010.1, F-011.3, F-014.2, F-020, F-017.3) | n/a | n/a | No LLM: Jinja2 templates | n/a | n/a |
| Embeddings for invoice search (F-105, v1) | later | `GEMINI_MODEL_EMBED` | `gemini-embedding-2` | n/a | n/a |

Rules:
- Model IDs live only in env vars and settings; no model ID string appears in code outside the settings defaults.
- The eval harness prints the model ID used per task, so results are comparable when a model is swapped.
- When a model is deprecated, change the env var and rerun `bk eval`; no code change.
- Rough cost at Flash-Lite: well under $0.01 per invoice extraction.

`gemini-flash-latest` style aliases are avoided: they hot-swap on new releases and would change eval results silently.

## 5. LangGraph layout

All graphs compile with one shared `AsyncPostgresSaver`. Thread ids: `invoice:<invoice_id>`, `boss:<telegram_user_id>`, `excel:<document_id>`.

| Graph | Nodes (LLM nodes marked *) | Interrupts |
| --- | --- | --- |
| Router (entry for every update) | `resolve_sender` (plain code: boss / active supplier / stranger, F-009.3) -> `stranger_flow` (template reply + boss card, F-010) or `supplier_flow` (file type check, store, ack, start invoice graph) or `boss_flow` (callback buttons parsed in code; free text -> `classify_intent`* -> assistant graph) | none |
| Invoice pipeline | `store_document` -> `extract`* (-> `extract_retry`* on failure) -> `validate_schema` -> `propose_entry` (plain code from supplier default account + GST rule, F-012.3) -> `run_checks` (one plain Python function per F-013.x, results to `check_results`) -> branch: `post` (transaction: entry + bill + TB check, F-014) -> `notify_fyi`; or `request_approval` -> `interrupt()` waiting for Approve / Edit / Reject / Ignore duplicate / Post anyway -> `post`, `revise`* -> `run_checks`, or `reject` | `request_approval`: resumed by `Command(resume={...})` from the Telegram callback handler after verifying the presser is the boss (F-015.8) |
| Boss assistant | `agent`* with tools. Read-only tools: `get_balances`, `get_pnl`, `list_bills`, `supplier_spend`, `get_entry`, `trial_balance` (all call the same report service as the web, F-018.2). Propose tools: `propose_manual_entry`, `propose_payment`, `propose_sales`, `propose_reversal`, `propose_opening_from_excel`. Propose tools build the entry in code, validate G-1/G-3, then `interrupt()` for Confirm / Edit / Cancel | Every propose tool. Nothing posts without the resume value `confirm` |

Rules enforced in code, not prompts: supplier and stranger flows never get ledger tools (NFR Permissions); outbound sends go through one `notify` service that only targets the boss chat or the sending supplier (NFR Prompt injection); document text is passed inside a delimited data part with a system instruction that it is data (G-5).

## 6. Scheduling

- APScheduler 3.11 `AsyncIOScheduler` starts in the FastAPI lifespan and runs a `tick` job every minute.
- `tick` reads business settings (recap time, reminder days, report day/time, timezone) and computes which slots are due: `daily_recap:2026-11-18`, `bill_reminders:2026-11-18`, `month_close:2026-11`.
- Guard: `INSERT INTO scheduled_runs (job, slot) ... ON CONFLICT DO NOTHING RETURNING id`; the job runs only if a row was inserted (F-020.3, NFR Reliability). Per-bill reminders also record `(bill_id, kind)` so each fires once (F-017.3).
- On startup, a catch-up pass runs any slot from today that was missed while the server was down.
- Why in-process: one deployment, one API container, no Redis. Settings changed on the web apply at the next tick without re-registering cron jobs (F-002.4). The DB guard makes a second process or restart harmless.

## 7. Files

- `STORAGE_DIR` (default `./storage`, Docker volume `/data/storage` in prod) holds originals under `invoices/YYYY/MM/<supplier-slug>/<sha256>.<ext>` plus `previews/<sha256>.jpg` for HEIC/photos (F-011.2).
- Postgres `documents` row: path (relative), sha256, mime, size, sender, received_at, kind. Same sha256 links to the existing row (F-011.4). Files are never deleted by the app.
- `GET /api/documents/{id}/file` streams with `FileResponse` only for a valid boss session; path is resolved from the DB, never from the URL (F-024.3, NFR Security).

## 8. Web (`web/`)

| Tool | Version | Why it fits (PRD) | Rejected alternatives |
| --- | --- | --- | --- |
| Vite | 8.3.8 | Fast dev server with `/api` proxy so cookies are same-origin; static build for Caddy | Next.js: rejected by user in favour of Vite SPA; FastAPI owns auth. Remix/React Router framework mode: SSR not needed |
| React | 19.3.1 | Current stable | Vue/Svelte: shadcn/ui is React |
| @vitejs/plugin-react | 6.3.0 | React fast refresh | SWC plugin: no need |
| TypeScript | 7.0.2 | Native (Go) compiler, default in `create-vite` 9.3.4 React template, much faster `tsc -b` | 6.0.3: only needed if a tool requires the JS compiler API (see Biome row). Note: TS 7 removed `baseUrl`; use `paths` only (`"@/*": ["./src/*"]`) and ignore the `baseUrl` line in shadcn docs |
| pnpm | 12.21.0 | Fast, strict installs, lockfile | npm/yarn: slower, looser hoisting |
| Tailwind CSS (+ `@tailwindcss/vite`) | 4.3.5 | Current major, CSS-first config, Vite plugin | Tailwind 3: legacy config |
| shadcn/ui CLI | 4.23.0 | `pnpm dlx shadcn@latest init -t vite`; copy-in components (Table, Tabs, Dialog, Form, Card, Chart) | MUI, Mantine: heavy theme systems, harder to match design |
| @phosphor-icons/react | 2.1.10 | Required icon set (also a shadcn dependency option) | lucide-react: shadcn default, replaced per brief |
| @fontsource-variable/montserrat | 5.3.0 | Self-hosted Montserrat (brief), no Google Fonts call | Google Fonts CDN: external request |
| TanStack Router (+ `@tanstack/router-plugin` 1.169.0, `@tanstack/zod-adapter` 1.167.0) | 1.170.46 | Type-safe, validated URL search params: date filters (F-024.2, F-025.2, F-028.4) and tabs live in the URL; `beforeLoad` auth guard (F-001.2) and setup redirect (F-002.1); pairs with TanStack Query loaders | React Router 8.5.1: solid, but search params are untyped strings and its focus is framework/SSR mode |
| TanStack Query (+ devtools) | 5.108.0 | Server state, caching per filter, `queryClient.clear()` on sign-out (F-001.3) | SWR: fewer features. Redux: unnecessary |
| Recharts (via `shadcn add chart`) | 3.x (shadcn pins 3.8.0; latest 3.10.1) | shadcn chart components wrap Recharts: bars and lines for F-028 | Nivo, ECharts: second styling system |
| react-hook-form + @hookform/resolvers | 7.92.0 + 7.0.7 | shadcn Form pattern; opening balances live debit/credit difference (F-004.2), settings validation (F-002.3) | Formik: less maintained |
| zod | 4.6.7 | Form and search-param schemas | yup: weaker TS inference |
| qrcode.react | 4.2.0 | QR code for the Telegram link (F-006.1) client-side | Python `qrcode` 8.2 server PNG: extra route for no gain |
| Biome | 2.6.8 | One tool for lint + format (`biome check`), fast, React/a11y rules. Does not depend on the TypeScript JS API, so it works with TS 7 | ESLint 10.15 + Prettier 3.10: typescript-eslint 8.73 peer range is `typescript <6.1.0`, so it cannot lint with TS 7; would force TS 6 and two configs. oxlint: lint only, still needs a formatter |
| Vitest | 5.1.0 | Unit/component tests, shares Vite config | Jest: separate transform config |
| @testing-library/react / jest-dom / user-event | 16.3.3 / 7.0.1 / 14.6.12 | Component behaviour tests | Enzyme: dead |
| jsdom | 31.0.1 | Vitest DOM environment | happy-dom: fine, jsdom more complete |
| msw | 3.0.6 | Mock `/api` in component tests | Hand-mocked fetch: brittle |
| Playwright (`@playwright/test`) | 1.65.1 | Browser flows against real API + Postgres (section 12) | Cypress: slower, weaker multi-tab |

## 9. Repo layout

```
AI-Bookkeeper/
  Makefile                      # top-level wrappers (section 10.3)
  docker-compose.yml            # postgres (always); api, web, caddy under profile "prod"
  Caddyfile                     # prod reverse proxy + HTTPS
  .env.example                  # names only, see section 11
  README.md                     # setup incl. credentials checklist (F-031.1)
  planning/
  scripts/
    dev-tunnel.sh               # ngrok http 8000 (or cloudflared) and print PUBLIC_BASE_URL
  storage/                      # gitignored; invoice files in dev
  api/
    pyproject.toml  uv.lock  alembic.ini  Dockerfile
    src/bookkeeper/
      main.py                   # app factory, lifespan (PTB app, scheduler, checkpointer)
      config.py                 # pydantic-settings, fail-fast env check
      cli.py                    # `bk` entry point: seed, eval, set-webhook, webhook-info, check-env
      db/ models.py session.py
      migrations/               # Alembic versions
      auth/                     # Google OAuth, sessions, test-login (test env only)
      web_api/                  # routers: settings, accounts, suppliers, users, assets, opening, journal, ledger, reports, analytics, documents, links
      telegram/                 # webhook route, PTB handlers, keyboards, notify service
      agents/
        llm.py                  # Gemini client wrapper, model per task, retries, audit
        graphs/ router.py invoice.py assistant.py
        tools/ readonly.py propose.py
        prompts/
      ledger/                   # posting service, checks/ (one module per F-013.x), periods, depreciation
      reports/                  # TB, ATB, P&L, BS, cash flow, AP aging (shared by web, bot, PDF)
      pdf/ templates/ render.py
      scheduler/ jobs.py slots.py
      storage/ files.py
      templates/                # Telegram message templates
    eval/
      seed/                     # demo cafe data (F-030.1)
      samples/clean/ samples/traps/
      expected.yaml             # sample -> expected outcome (F-030.2)
      runner.py                 # real pipeline, prints table, exit code (F-030.3)
    tests/ unit/ integration/ conftest.py
  web/
    package.json  pnpm-lock.yaml  vite.config.ts  tsconfig.json  tsconfig.app.json  tsconfig.node.json
    biome.json  components.json  vitest.config.ts  playwright.config.ts  Dockerfile  Caddyfile.static
    src/ main.tsx routes/ components/ui/ features/ lib/api.ts lib/query.ts
    e2e/                        # Playwright specs
```

`eval/` lives inside `api/` so it imports the package and uses the same uv environment.

## 10. Commands

### 10.1 API (run in `api/`)

| Purpose | Command |
| --- | --- |
| Install | `uv sync` |
| Dev server | `uv run uvicorn bookkeeper.main:app --reload --port 8000` |
| Lint | `uv run ruff check .` |
| Format | `uv run ruff format .` (CI: `uv run ruff format --check .`) |
| Typecheck | `uv run mypy src tests` |
| Unit tests | `uv run pytest -m "not integration"` |
| Integration tests | `uv run pytest -m integration` |
| All tests + coverage | `uv run pytest --cov=bookkeeper` |
| Migrate | `uv run alembic upgrade head` |
| New migration | `uv run alembic revision --autogenerate -m "<msg>"` |
| Seed demo cafe | `uv run bk seed` |
| Eval harness | `uv run bk eval` (non-zero exit on any fail) |
| Set webhook | `uv run bk set-webhook` (calls `setWebhook` with `PUBLIC_BASE_URL/telegram/webhook`, `secret_token=TELEGRAM_WEBHOOK_SECRET`, `allowed_updates=["message","callback_query"]`) |
| Webhook status | `uv run bk webhook-info` |
| Check env | `uv run bk check-env` |

### 10.2 Web (run in `web/`)

| Purpose | Command |
| --- | --- |
| Install | `pnpm install` |
| Dev server | `pnpm dev` (Vite on 5173, proxies `/api` to `http://localhost:8000`) |
| Lint | `pnpm lint` -> `biome lint .` |
| Format | `pnpm format` -> `biome format --write .` |
| Lint + format check (CI) | `pnpm check` -> `biome check .` |
| Typecheck | `pnpm typecheck` -> `tsc -b --noEmit` |
| Unit/component tests | `pnpm test` -> `vitest run` |
| E2E | `pnpm e2e` -> `playwright test` (first time: `pnpm exec playwright install --with-deps chromium`) |
| Build | `pnpm build` -> `tsc -b && vite build` |
| Add shadcn component | `pnpm dlx shadcn@latest add <name>` |

### 10.3 Top-level Makefile

Make is preinstalled on macOS and Linux, so cloners need nothing extra (`just` 1.59.0 rejected for that reason only).

| Target | Runs |
| --- | --- |
| `make setup` | `cp -n .env.example .env`, `cd api && uv sync`, `cd web && pnpm install` |
| `make db` | `docker compose up -d postgres` |
| `make migrate` / `make seed` | api migrate / seed |
| `make api` / `make web` | api dev / web dev |
| `make tunnel` | `scripts/dev-tunnel.sh` |
| `make webhook` | api set-webhook |
| `make lint` / `make format` / `make typecheck` | both projects |
| `make test` | api pytest (all) + web vitest |
| `make e2e` | web Playwright |
| `make eval` | api eval |
| `make check` | lint + typecheck + test (pre-commit/CI gate) |
| `make prod-up` | `docker compose --profile prod up -d --build` |

### 10.4 Dev and prod flow

- Dev: `make db migrate seed`, then `make api`, `make web`, `make tunnel` (ngrok 3.39.13: `ngrok http 8000`, or `cloudflared tunnel --url http://localhost:8000` with cloudflared 2026.11.1), set `PUBLIC_BASE_URL` to the tunnel URL, `make webhook`. A free ngrok static domain avoids re-registering the webhook on every restart (plan details not verified on 2026-11-18).
- Prod: on any VPS with Docker, point DNS A record at the server, fill `.env`, `make prod-up`. The api container runs `alembic upgrade head` then uvicorn; Caddy gets certificates automatically; run `docker compose exec api bk set-webhook` once.

## 11. Environment variables (names only)

| Name | Purpose |
| --- | --- |
| `APP_ENV` | `dev`, `test` or `production`; controls cookie `Secure`, test-login availability |
| `TZ_DEFAULT` | Business timezone used before setup completes (default `Asia/Singapore`, G-6) |
| `DATABASE_URL` | Postgres URL (`postgresql+psycopg://...`) for SQLAlchemy and the LangGraph checkpointer |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | Used by the Postgres container |
| `STORAGE_DIR` | Folder for invoice files and previews |
| `PUBLIC_BASE_URL` | HTTPS origin Telegram can reach; webhook = this + `/telegram/webhook` |
| `WEB_APP_URL` | Origin of the web app for links in Telegram messages (F-023.2); equals `PUBLIC_BASE_URL` in prod, `http://localhost:5173` in dev |
| `DOMAIN` | Hostname Caddy serves and certifies in prod |
| `TELEGRAM_BOT_TOKEN` | Bot API token from BotFather |
| `TELEGRAM_BOT_USERNAME` | Bot username for `t.me/<bot>` links (F-006, F-007, F-029); also exposed to the web via `/api/config` |
| `TELEGRAM_WEBHOOK_SECRET` | Value sent by Telegram in `X-Telegram-Bot-Api-Secret-Token` (F-009.1), 1 to 256 chars of `A-Z a-z 0-9 _ -` |
| `GOOGLE_CLIENT_ID` | OAuth client id |
| `GOOGLE_CLIENT_SECRET` | OAuth client secret |
| `GOOGLE_REDIRECT_URI` | Exact callback URL registered in Google Cloud (not derived from request host, so the Vite proxy works) |
| `BOSS_EMAIL` | Only Google account allowed to sign in (F-001.1) |
| `SESSION_SECRET` | Key for signing the session cookie |
| `SESSION_MAX_AGE_DAYS` | Session lifetime |
| `GEMINI_API_KEY` | Gemini API key from AI Studio |
| `GEMINI_MODEL_EXTRACT` | Invoice extraction model |
| `GEMINI_MODEL_EXTRACT_ESCALATE` | Escalation model for hard documents; empty disables |
| `GEMINI_MODEL_REVISE` | Edit-instruction revision model |
| `GEMINI_MODEL_EXCEL_MAP` | Excel mapping model |
| `GEMINI_MODEL_ASSISTANT` | Boss Q&A and propose-entry agent model |
| `GEMINI_MODEL_SALES` | Sales parsing model |
| `GEMINI_MODEL_ROUTER` | Boss intent classification model |
| `GEMINI_MODEL_REPLY` | Short reply writer model |
| `GEMINI_MODEL_EMBED` | Embedding model (v1, F-105) |
| `LLM_TIMEOUT_SECONDS` | Per-call timeout before retry |
| `LOG_LEVEL` | Log verbosity |
| `E2E_TEST_LOGIN` | Enables `/api/test/login` only when `APP_ENV=test`; app refuses to start if set with `APP_ENV=production` |
| `TEST_DATABASE_URL` | Optional: run integration tests against compose Postgres instead of testcontainers |
| `NGROK_AUTHTOKEN` | Used by `scripts/dev-tunnel.sh` |

## 12. Testing strategy

| Layer | Tool | What | LLM |
| --- | --- | --- | --- |
| Accounting math and rules | pytest + hypothesis | G-1 balance check, Decimal rounding, GST split (inclusive/exclusive), depreciation schedule (F-021.2), period lock date moves (G-3), reversal pairs (G-2), statement identities (assets = liabilities + equity, cash flow ties to cash change) | none |
| Deterministic checks | pytest | One test module per F-013.x with pass and fail fixtures, including tolerances | none |
| Graph logic | pytest + fake LLM | `LLMClient` protocol injected; fake returns canned schema objects. Asserts routing by role, interrupt on any failed check, no ledger tools in supplier/stranger graphs, stranger reply text contains no business data (brief success metric) | mocked |
| Integration | pytest `-m integration` + testcontainers (`pgvector/pgvector:0.8.7-pg18-trixie`) | Alembic migrate from empty, posting transactions, NUMERIC/JSONB round trips, duplicate update id ignored (F-009.2), scheduler slot guard under double run (F-020.3), webhook rejects bad secret (F-009.1), full invoice flow via fake Telegram updates posted to `/telegram/webhook` with a recording fake `Bot`, approval resume via callback, `AsyncPostgresSaver` survives app restart mid-interrupt, OAuth callback allow/deny with mocked Google token | mocked |
| Eval harness | `bk eval` | Every clean and trap sample through the real pipeline with real Gemini and a fresh seeded DB; asserts F-030.4. Records model IDs used. Run before changing any model env var | real |
| Web unit/component | Vitest + Testing Library + msw | Opening-balance live difference and blocked save, settings validation, date filter to URL params, tables totals display, auth guard redirect | n/a |
| Browser e2e | Playwright | Sign-in via test login, first-run setup redirect, Connect Telegram shows link + QR, supplier invite, journal filters and totals equal, entry detail opens document, analytics renders, sign-out then back button shows no data | n/a |

Test-login bypass: `POST /api/test/login` is registered only when `APP_ENV=test` and `E2E_TEST_LOGIN=1`; it creates a normal session for `BOSS_EMAIL`. Startup aborts if `E2E_TEST_LOGIN` is set in any other env, and an integration test asserts the route returns 404 when the flag is off. Playwright `webServer` starts the API (test env, test DB, seeded) and Vite.

## 13. Credentials the owner must create

- [ ] Telegram bot: in Telegram open @BotFather, `/newbot`, choose display name, choose a username ending in `bot` -> copy token to `TELEGRAM_BOT_TOKEN` and username (without @) to `TELEGRAM_BOT_USERNAME`. Optional: `/setdescription`, `/setuserpic`. Keep privacy mode on (bot is used in private chats).
- [ ] Webhook secret: generate a random string (e.g. `openssl rand -hex 32`) -> `TELEGRAM_WEBHOOK_SECRET`.
- [ ] Google Cloud project: create a project at console.cloud.google.com.
- [ ] OAuth consent screen (Google Auth Platform): user type External, app name, support email, scopes `openid`, `email`, `profile`; while in Testing status add `BOSS_EMAIL` as a test user (or publish; these scopes need no verification).
- [ ] OAuth client: Credentials -> Create OAuth client ID -> Web application.
  - Authorized JavaScript origins: `http://localhost:5173` (dev), `https://<your-domain>` (prod).
  - Authorized redirect URIs: `http://localhost:5173/api/auth/callback` (dev, via Vite proxy), `https://<your-domain>/api/auth/callback` (prod).
  - Copy client id and secret to `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`; set `GOOGLE_REDIRECT_URI` to the matching URI.
- [ ] `BOSS_EMAIL`: the Google account that will sign in.
- [ ] `SESSION_SECRET`: `openssl rand -hex 32`.
- [ ] Gemini API key: aistudio.google.com -> Get API key -> create key -> `GEMINI_API_KEY`. Enable billing on the project if using `gemini-4-argon` escalation (no free tier) or beyond free-tier limits.
- [ ] ngrok (dev): sign up, copy authtoken -> `ngrok config add-authtoken <token>` (or `NGROK_AUTHTOKEN`); optionally claim the free static domain. Alternative: cloudflared quick tunnel (no account) or a named Cloudflare tunnel.
- [ ] Prod domain: buy or reuse a domain, create an A (and AAAA) record to the VPS IP, open ports 80 and 443, set `DOMAIN`, `PUBLIC_BASE_URL=https://<domain>`, `WEB_APP_URL=https://<domain>`.

## 14. Could not verify / to re-check

- Whether `gemini-4-hydrogen` and `gemini-3.5-flash-lite` have any deprecation date: none was listed on 2026-11-18.
- Gemini inline request size limit for PDFs/images (decides inline bytes vs Files API for 20 MB uploads, F-011.1): plan uses Files API above a configurable threshold; confirm limit at build time.
- `gemini-embedding-2` pricing (v1 only).
- Whether shadcn CLI 4.23 handles a `tsconfig` with `paths` but no `baseUrl` under TS 7 without warnings; fallback is TypeScript 6.0.3.
- ngrok free plan static domain availability (agent version 3.39.13 confirmed).
- Gemini 4 model naming is new (no "Pro"/"Flash" labels); class mapping above is from the models page descriptions and launch coverage of Hydrogen as the 3.8 Flash successor.
