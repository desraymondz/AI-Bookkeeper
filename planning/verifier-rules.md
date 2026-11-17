# Verifier rules

See planning/decisions.md#D-032. You are blind: you get the task ID, branch or worktree, doc paths and T-xxx list, never the builder's report. Read-only on code; never commit, tick or push. Never read `.env*`.

## White-box review
- Read the task's PRD sections, `02-design.md` (UI tasks), the decisions named there, the T-xxx rows, then `git diff preview...<branch>`.
- Judge the code against the docs only: acceptance criteria met; tests really test the T-xxx behaviour (not tautologies); security and role rules; design tokens (no hard-coded colours); file ownership (`planning/builder-rules.md`); no secrets; comment policy; no raw journal writes outside `bookkeeper.ledger`.

## Commands (scoped, quiet)
- Run only the task's own tests, quietly: `uv run pytest -q --no-header --tb=short -rfE <task test paths>`, `pnpm test --reporter=dot <task test files>`, and for UI tasks `pnpm e2e --reporter=dot <task specs>`.
- Do not run full lint, typecheck, the full suite or the build: the builder's gate covers them and the orchestrator runs `make verify QUIET=1` on `preview` after each merge and `make e2e QUIET=1` once per batch.
- Run a full command only if the diff touches shared infrastructure (Makefile, conftest, `tests/support`, `routes.py`, `main.py`, migrations, config) or a scoped run fails in a way that suggests a wider break.

## Browser test (UI tasks only)
- Start the app with mock data or the test-login bypass. Walk each browser T-xxx.
- Full-page screenshots before (on `preview`) and after (on the branch) for every changed screen: `planning/evidence/<task-id>/before-<screen>.png`, `after-<screen>.png`.

## Report (max 20 lines)
`VERDICT: PASS | FAIL`, a line per T-xxx, issues as `file:line: problem (doc reference)`, command results with counts, screenshot paths.
