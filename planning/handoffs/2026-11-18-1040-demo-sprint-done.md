# Handoff: demo-sprint-done
Date: 2026-11-18 10:40 SGT   Branch: preview   Last commit: 5c39f60 fix(S-6): verifier findings on bill payment, clarify cap, totals warning

## Goal
The 6-hour portfolio prototype (D-036) is built. What is left is running the real-Gemini eval and the live Telegram demo, then optionally starting the deferred v1 items.

## State
- Done: D-036 scope cut; S-1 to S-6 in planning/build-plan.md#demo-sprint-d-036. Commits 9149ef9..5c39f60 are on `preview` and nothing is pushed. A blind verifier gave PASS, and its minor findings were fixed in 5c39f60.
- Built:
  - S-1: demo e2e test.
  - S-2: boss assistant. Q&A, manual entry, sales by text, `/bills` and Mark paid, all behind Confirm.
  - S-3: `/recap`.
  - S-4: web Journal with entry sheet, TB, P&L and BS.
  - S-5: `bk eval` harness, `bk set-webhook`, `bk webhook-info`, scripts/dev-tunnel.sh and README.md.
- Not started:
  - The real-Gemini `make eval` has not been run.
  - Gate rows still open until it runs: T-097, T-210, T-214, T-216, T-218, T-222, T-225, T-228, T-229.
  - The live Telegram demo has not been tried with real credentials.
  - Every item D-036 defers.
- Checks:
  - `make verify QUIET=1` green: api 454, web 46.
  - `make e2e QUIET=1`: 33 passed.

## Decisions this session
- D-036 (in decisions.md): sprint scope, gate and deferred rows, and the lighter process (D-031 and D-032 suspended for the sprint).
- Boss Confirm step is a held PROPOSED journal entry, not a LangGraph interrupt. Module is agents/boss.py, not agents/graphs/boss.py (build-plan S-2 row updated).
- Sales text is parsed in code (agents/boss.py parse_sales). The LLM only handles other boss text, and only proposes.
- Answers, recap and proposals are Jinja templates. The only LLM text shown is the clarifying question, capped at 200 chars.
- Recap "Sales booked" is gross (revenue plus Output GST), to match T-167.
- `/api/reports/trial-balance` now also takes the range params; as_at defaults to the range end.
- Eval expected outcomes live in api/eval/expected.toml (stdlib tomllib) instead of yaml, so no new dependency. Samples are PDFs built in code (api/eval/samples/).
- Deferred tabs (GL, ATB, Cash flow) are hidden from the accounting nav. Their routes still exist as placeholders.

## User said
- Prototype is a portfolio and interview demo, Telegram first with a thin web, built in about 6 hours. The user OK'd lightening the process.
- Do not push. Never read `.env*`. Subagents run on Sonnet. Real creds are used only for `make eval` and the live demo, and only on the owner's OK.

## Gotchas and dead ends
- Handler order: first match wins. routes.py imports are isort-sorted, so import order is not registration order. Boss handlers must stay last (boss.register()).
- Unmocked calls in tests reach real Gemini through services.llm_for. Use services.override(llm=...) or queue FakeLLMClient results.
- The posted-journal ORM guard refuses bulk UPDATE on journal tables even for held rows. Set attributes and flush instead.
- Alembic env.py calls asyncio.run. From async code, run migrations in a thread (eval/runner.py).
- The Stop hook (20s unit / 15s web cap) reports failures under load from parallel runs. The tests pass when rerun alone.
- A Bash heredoc containing JSX with `$` was blocked by a safety parser. Write such files with the Write tool.

## Open questions
- Run `make eval` with real Gemini now? This needs the owner's OK because it reads real creds.
- The revoked-users listing, the Stop hook timeout, and the D-029 and D-030 defaults are still open (unchanged).

## Next steps
1. Owner OK, then `make db`, then `make eval`. Tick the eval gate rows that pass and log any fails.
2. Live demo per the README "Run it locally" and "Demo script" sections. This needs ngrok, `make webhook`, and two Telegram accounts.
3. Optional: a PR from `preview` to `main` for the owner to merge.
4. After that, pick deferred items from D-036. Suggested order: scheduler for the recap, opening balances, GL tab.

## Read first
- planning/progress.md
- planning/decisions.md#D-036
- planning/build-plan.md (Demo sprint section at the end)
- README.md

## Resume prompt
> Paste this into a fresh session:
> Read planning/handoffs/2026-11-18-1040-demo-sprint-done.md and the files under "Read first". Then ask me before running `make eval` with real Gemini, and help me run the live Telegram demo from the README.
