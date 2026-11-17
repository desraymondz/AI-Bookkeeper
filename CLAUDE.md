@AGENTS.md

## Claude Code specifics
- Build with the `des-build` skill. It reads `planning/` and uses `planning/04-test-spec.md` as the merge checklist.
- When a session gets long or a phase ends, run `des-handoff` to write `planning/handoffs/<date>-<topic>.md`.
- Hooks in `.claude/hooks/` block edits to `.env*` and to test-spec expected results, lint each edited file, and run fast unit tests on stop.
