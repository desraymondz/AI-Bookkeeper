# AI log

| Date | Phase | What the AI did | What was wrong | How it was corrected |
| --- | --- | --- | --- | --- |
| 2026-11-18 | Brief | Read the raw notes as "no reply" and "short reply" for strangers | The notes contradicted each other; the AI could not pick one safely | Asked the user; chose short neutral reply + ask boss (D-005) |
| 2026-11-18 | Brief | Assumed an expenses-only scope from the notes | P&L, cash flow and margins need revenue | Asked; added daily sales via Telegram (D-002) |
| 2026-11-18 | Stack | Planned Next.js with Auth.js per the brief | User switched to Vite + Vitest after the brief was locked | Replanned web as Vite SPA, moved Google OAuth into FastAPI (D-012, D-013) |
| 2026-11-18 | Stack | Stack draft used gemini-4-hydrogen and gemini-4-argon for heavier tasks | User wants the cheapest model first and swappable models | All tasks default to gemini-3.5-flash-lite via per-task env vars; upgrade only on eval failure (D-016) |
