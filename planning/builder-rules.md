# Builder rules

See planning/decisions.md#D-031 and #D-032. Every builder reads this file before starting.

## Scope
- Touch only the files your card owns. Need a shared file changed (Makefile, compose, `.env.example`, pyproject, lockfiles, `db/models.py`, migrations, `web/src/routeTree.gen.ts`, AGENTS.md, `planning/*`)? Put the exact change in your report.
- Register routers only by appending to `api/src/bookkeeper/routes.py`.
- New dependencies: add them and commit the updated lockfile in the same commit; `make deps-check` must pass.
- Never read or edit `.env*`. Never push. Never tick `planning/04-test-spec.md`.

## Tests
- Write the tests for your T-xxx first, from the test spec wording, then implement until they pass.
- Integration tests use `api/tests/support` (real `create_app`, stub boss, factories through the ledger service, FakeLLMClient, RecordingBot, telegram_updates). No task-local app builders, fakes or raw journal inserts. E2E uses `web/e2e/support` only.

## Code
- Comments only point to other files or docs (`See planning/decisions.md#D-004`, `See src/lib/x.ts`). No comments that justify choices, claim correctness or describe expected behaviour. No TODO without a task ID.
- Follow the hard rules in AGENTS.md (Decimal money, ledger posting service for every journal write, LLM proposes and code decides, templates for fixed replies, model IDs from env, no em dashes in copy).
- The lint-on-edit hook may run `ruff --fix`: add an import and its use in the same edit.

## Output size
- Run every command quietly: `make verify QUIET=1`, `make e2e QUIET=1`, `uv run pytest -q --no-header --tb=short -rfE <scope>`, `pnpm test --reporter=dot`. Read only the failures and the summary line.

## Done gate
1. Your T-xxx tests green in isolation.
2. `scripts/wt.sh integrate` (merges latest `preview`, runs `make sync`). Resolve conflicts, keeping both sides of route registry, `CHECKS` list and lockfile changes.
3. `make verify QUIET=1` green on the integrated branch; UI cards also `make e2e QUIET=1`.
4. Commit: `<type>(<task-id>): <summary>` (conventional commits), then commit the merge.

## Report (max 12 lines, no code)
Files changed, tests added (T-xxx), isolated and full verify counts, integrated `preview` SHA, shared-file requests, interface notes other tasks need, blockers.
