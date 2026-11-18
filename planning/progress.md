# Progress

Phase: Demo sprint per D-036 (2026-11-18): P3 to P6 paused, 6-hour portfolio prototype, Telegram first with thin web. Next: S-1 end-to-end demo test, then S-2 to S-6 in planning/build-plan.md#demo-sprint-d-036. P1 and P2 DONE (api 428, web 37, e2e 33). D-031/D-032 suspended for the sprint.

| Doc | Status |
| --- | --- |
| 00-brief.md | Locked |
| 01-prd.md | Locked (F-013.10 added via D-025) |
| 02-design.md | Locked |
| 03-tech-stack.md | Locked (all models Flash-Lite via D-016) |
| 04-test-spec.md | Locked |
| decisions.md | D-001 to D-036 |
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
| 2026-11-18 | B3 | P1-T08 demo cafe seed | FAIL (comment policy, self-ticked spec) then fix round, re-verify PASS, merged; T-209 ticked |
| 2026-11-18 | B3 | P1-T06 reports service | Verifier PASS, merged; T-009, T-202 ticked; reports/ledger routers wired; auth stubs moved to /api/stub-*; D-030 |
| 2026-11-18 | P2 | P2-T00 integration harness | Builder cut off uncommitted; Sonnet builder finished; verifier PASS (api 241, web 26, e2e 24), merged; make hooks and make sync run in main checkout |
| 2026-11-18 | B4 | P2-T07 Gemini client, extraction, proposal | Verifier PASS (scoped, D-032), merged; T-044, T-098, T-101..T-104 ticked; T-100 ticks with P2-T08 (boss card); preview verify green api 254 web 26 |
| 2026-11-18 | B4 | P2-T01 webhook, routing, notify, templates | Verifier PASS with G-5 gap (raw bot on HandlerContext); fix round added notify facade and tg_app fixture in tests/support; orchestrator checked fix (35 tests, no bypass grep), merged; lifespan drains telegram tasks; T-014, T-078..T-081 ticked; preview api 267 web 26 |
| 2026-11-18 | B4 | P2-T05 checks F-013.1..5 | Reconciled to T07 schema; verifier FAIL (sha rule matched own document, tautological T-114); fix round added current_invoice_id; re-verify PASS; merged; T-036, T-105..T-116, T-240 ticked; T-125 ticks with P2-T06; preview api 303 web 26 |
| 2026-11-18 | B5 | P2-T04 invoice intake and storage | Verifier PASS (scoped + shared infra), merged; T-090..T-096, T-245 ticked; D-033 re-send reuses Document row; HANDLER_MODULES list in routes.py loads handler modules |
| 2026-11-18 | B4 | P2-T06 checks F-013.6..10 | Re-integrated on T05/T07; verifier PASS; merged; T-117..T-125, T-239 ticked; T-233..T-235 held for D-034 (document text gap, fixed in P2-T08). B4 complete. |
| 2026-11-18 | B5 | P2-T02 linking, suppliers, users API | Verifier PASS (scoped + shared infra), merged; migration 0003 trade_payable on account 2000 (D-030 closed); T-058..T-062, T-064, T-068..T-070, T-075..T-077, T-202 ticked; agents/tool_gate.py for P2-T08; preview api 371 web 26 |
| 2026-11-18 | B5 | P2-T03 stranger handling | Pre-verify fix (ctx._bot), verifier FAIL (bypass still present despite report, Ref S<n> spoof, silent rejections), fix round 2, re-verify PASS, merged; T-082..T-089, T-238 ticked; T-237 held for P3-T04 recap. B5 complete. B6 (P2-T08, P2-T09) building. |
| 2026-11-18 | B6 | P2-T09 web suppliers, users, Connect Telegram | Verifier PASS with browser walk-through, merged; T-057, T-063, T-065..T-067, T-071..T-074 ticked; T-024 web flake fixed (MSW in-flight wait); evidence in planning/evidence/P2-T09/ |
| 2026-11-18 | B6 | P2-T08 invoice LangGraph and approvals | Orchestrator ran full verify (api 417, web 37), verifier PASS, merged; D-034 closed; migration 0004 DB immutability trigger (D-035); 23 rows ticked incl. T-233..T-235, T-100; T-011 at P4-T02, T-140/T-237 at P3-T04; P2-T10 hardening card added |
| 2026-11-18 | B6 | P2-T10 invoice pipeline hardening | Verifier PASS, merged; trigger raw-SQL tests, boss notice on refused post, resume undo, services close, edit text only on reply to prompt; T-005 DB layer proven (ticks at P4-T02) |

## P1 phase summary
- Built: API and web scaffolds, ledger posting service and periods, Google auth and sessions, settings and chart of accounts, reports service, web sign-in/setup/settings/accounts, demo cafe seed.
- Ticked: 46 rows. Deferred by plan: T-005, T-011 (all write paths), T-036 second half (P2-T05), T-044 (P2-T07).
- Decisions: D-026 to D-031. Corrections: planning/ai-log.md (6 build rows).
- Known cosmetic: duplicate "Business" heading on /settings/business.

## P2 phase summary
- Built: integration harness (D-031), Telegram webhook, routing, notify facade (G-5), linking and suppliers/users API, stranger handling, invoice intake and storage, ten F-013 checks, Gemini extraction and proposal, invoice LangGraph with auto-post, approval cards, revisions, duplicate handling, hardening; web suppliers, users, Connect Telegram.
- Migrations: 0003 trade_payable subtype (D-030 closed), 0004 posted-journal immutability trigger (D-035).
- Decisions: D-032 to D-035. Corrections: planning/ai-log.md (P2 rows).
- Held rows: T-005, T-011 (P4-T02), T-140, T-237 (P3-T04).
- Gaps carried: no single end-to-end P2 demo test (P3-T00); revoked users vanish on reload (decide in P3); Stop hook 45s timeout trips under parallel load (owner to decide); seed.ts raw journal insert (replace by P5-T01).
- Evidence: planning/evidence/P2-T09/, planning/evidence/P2-phase/.

## Demo sprint (D-036)
- Scope cut recorded 2026-11-18. Sprint tasks S-1 to S-6 in planning/build-plan.md; gate and deferred rows in planning/decisions.md#D-036.
- Deferred: opening balances form, Excel migration, scheduler and reminders, partial and text payments, reversal by chat, assets, month-end close, PDF pack, GL, ATB and cash-flow tabs, analytics, most traps, prod self-host.
