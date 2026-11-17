# AI log

| Date | Phase | What the AI did | What was wrong | How it was corrected |
| --- | --- | --- | --- | --- |
| 2026-11-18 | Brief | Read the raw notes as "no reply" and "short reply" for strangers | The notes contradicted each other; the AI could not pick one safely | Asked the user; chose short neutral reply + ask boss (D-005) |
| 2026-11-18 | Brief | Assumed an expenses-only scope from the notes | P&L, cash flow and margins need revenue | Asked; added daily sales via Telegram (D-002) |
| 2026-11-18 | Stack | Planned Next.js with Auth.js per the brief | User switched to Vite + Vitest after the brief was locked | Replanned web as Vite SPA, moved Google OAuth into FastAPI (D-012, D-013) |
| 2026-11-18 | Stack | Stack draft used gemini-4-hydrogen and gemini-4-argon for heavier tasks | User wants the cheapest model first and swappable models | All tasks default to gemini-3.5-flash-lite via per-task env vars; upgrade only on eval failure (D-016) |
| 2026-11-18 | Build B2 | P1-T05 test helper registered routers itself and called them unauthenticated | Once main.py wired them behind require_boss, 23 tests got 401 and routers were double-registered | Orchestrator changed tests/integration/settings/app.py to use create_app routes and override require_boss with a stub boss |
| 2026-11-18 | Build B2 | Orchestrator edited main.py in two Edit calls | Lint-on-edit hook (ruff --fix) removed the new imports after the first edit because they were unused at that moment | Rewrote main.py in one Write; for shared Python files, apply imports and usage in a single edit |
| 2026-11-18 | Build B2 | Opus builder for P1-T03 stopped at the 5-hour usage limit | Work left uncommitted in the worktree | Orchestrator committed it as WIP, merged preview in (69 ledger tests green), handed to a Sonnet builder to finish |
| 2026-11-18 | Build B3 | P1-T08 builder wrote explanatory comments in seed data and ticked T-209 in the test spec itself | Comment policy breach; planning files are orchestrator-owned | Verifier FAIL; fix card sent to a new builder (remove comments, revert tick); re-verify with a fresh verifier |
| 2026-11-18 | Build P2 | P2-T00 builder session ended before committing; it also edited web/vite.config.ts and e2e specs outside the card's owned files | Work sat uncommitted in the worktree; ownership drift | New Sonnet builder finished from the partial state; blind verifier judged the extra files justified (per-worktree API port, import moves) and PASS |
