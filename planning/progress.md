# Progress

Phase: Build P1 Foundation (2026-11-18). Build plan approved: planning/build-plan.md (D-026). B1 merged. B2 merged (P1-T03, T04, T05). B3: P1-T07 web building; P1-T06 reports and P1-T08 seed next. Subagents now run on Sonnet 5.5 per owner (2026-11-18). Next after B2: B3 (P1-T06 reports, P1-T07 web auth/settings/accounts, P1-T08 seed).

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
| 2026-11-18 | B2 | P1-T05 settings, CoA, /api/config | Verifier PASS, merged; T-017, T-035, T-038, T-043 ticked; T-036 first half done (ticks in P2-T05); D-029 price rule options |
| 2026-11-18 | B2 | P1-T04 auth API | Verifier PASS, merged; T-025, T-026, T-029 ticked; settings/accounts/config routers wired in main.py behind require_boss |
| 2026-11-18 | B2 | P1-T03 ledger posting | Verifier PASS (Sonnet), merged; T-001..T-004, T-006..T-008, T-236 ticked; migration 0002 FK RESTRICT |
| 2026-11-18 | B3 | P1-T07 web auth, setup, settings, accounts | Verifier PASS (Sonnet), merged; 14 browser rows ticked; evidence in planning/evidence/P1-T07/ |
