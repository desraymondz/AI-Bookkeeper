# Progress

Phase: Build P1 Foundation (2026-11-18). Build plan approved: planning/build-plan.md (D-026). B1 merged. Next: batch B2 (P1-T03 ledger, P1-T04 auth, P1-T05 settings/CoA/config).

| Doc | Status |
| --- | --- |
| 00-brief.md | Locked |
| 01-prd.md | Locked (F-013.10 added via D-025) |
| 02-design.md | Locked |
| 03-tech-stack.md | Locked (all models Flash-Lite via D-016) |
| 04-test-spec.md | Locked |
| decisions.md | D-001 to D-025 |
| ai-log.md | 4 corrections logged |
| AGENTS.md, CLAUDE.md, .claude/ hooks | Written |

Scope: 31 MVP features (F-001 to F-031), 127 acceptance criteria plus 8 global rules. 245 tests (unit 39, integration 68, e2e 57, browser 55, eval 26).

Stack: FastAPI + LangGraph + python-telegram-bot + Postgres 18/pgvector (uv, ruff, mypy, pytest); Vite + React + TS 7 + Tailwind 4 + shadcn/ui + Phosphor (pnpm, Biome, Vitest, Playwright); Gemini `gemini-3.5-flash-lite` for every task.

Next step: run des-build. Owner must first create credentials in planning/03-tech-stack.md section 13 and fill `.env`.

Open questions (re-check at build time, see 03-tech-stack.md section 14):
- Gemini inline size limit for PDFs/images vs Files API.
- shadcn CLI with TS 7 (fallback TS 6.0.3, D-022).
- ngrok free static domain availability.

## Build log
| Date | Batch | Tasks | Result |
| --- | --- | --- | --- |
| 2026-11-18 | Setup | preview branch, build plan, D-026, push-to-main denies | Done |
| 2026-11-18 | B1 | P1-T02 web scaffold | Verifier PASS, merged; T-208 ticked; evidence in planning/evidence/P1-T02/ |
| 2026-11-18 | B1 | P1-T01 API scaffold | Verifier PASS, merged; T-232 ticked; D-028 tenacity pin |
