---
name: "des-build"
description: "Orchestrate a des-plan project: plan mode build order, parallel builder subagents in worktrees, blind verifier (code + browser with screenshots), merges to preview, PR to main. Use for /des-build."
---

# des-build: the orchestrator

You are the **orchestrator**. You plan, delegate, judge reports and merge. You do not write feature code yourself, and you do not read full diffs: subagents do the work in their own context and return short reports. All state lives in files so any fresh session can resume.

Roles:
- **Orchestrator** (this session): strongest model available, Fable if present, else Opus. If the session runs on a smaller model, tell the user to switch with `/model` before continuing.
- **Builder** subagents: implement one task card each.
- **Verifier** subagent: blind white-box review plus optional browser test. Always a fresh subagent, never the builder.

## Step 0: Preconditions and setup questions

1. Read `planning/progress.md`, `01-prd.md`, `03-tech-stack.md`, `04-test-spec.md`, `decisions.md`, `AGENTS.md`. If planning docs are missing or unlocked, stop and tell the user to run **des-plan**.
2. If resuming, read the latest `planning/handoffs/` file and `planning/build-plan.md`, then continue from the first unfinished task.
3. Ask once with AskUserQuestion:
   - Builder model: Sonnet (recommended, cheaper) or Opus
   - Verifier model: Opus (recommended) or Sonnet
   - Browser testing: allowed or not, and which tool is available (Claude in Chrome, Playwright MCP, none)
   - Test data: do they have mock data or a demo account? If login is needed, ask them to put credentials in `.env.local` (gitignored). Never invent credentials and never write them into docs.

## Step 1: Build plan (plan mode)

Enter plan mode (ask the user to press Shift+Tab if you cannot switch yourself). Read the docs and produce `planning/build-plan.md`:

- **Phases** (P1, P2 ...) that each end in something demoable
- **Tasks** as cards:

```
### P1-T03  Ledger post_entry service
Feature: F-002.1, F-002.3     Tests: T-010, T-011, T-012
Owns files: src/ledger/post.ts, src/ledger/post.test.ts
Reads: planning/01-prd.md#F-002, planning/decisions.md#D-004
Depends on: P1-T01
Verify: npm run lint && npm run typecheck && npm test -- ledger && npm run build
UI change: no
```

- **Dependency graph** and **batches**: tasks in the same batch share no owned files and do not depend on each other. Everything else is sequential.
- **Shared files** (package.json, lockfiles, route index, schema, env example, AGENTS.md, planning/*) are orchestrator-owned: builders request changes in their report; you apply them after merge.
- **Hooks audit**: read `.claude/settings.json`; list missing guardrails (lint on edit, block `.env*`, quick tests on Stop, block push to main) and add them after approval.

Exit plan mode with the plan for the user's approval. Log the build order rationale as a D-xxx entry.

## Step 2: Git setup

- Ensure `main` exists and is clean. Create `preview` from `main` if missing.
- `main` = production, only changed through a reviewed PR. `preview` = integration, everything merges here first.
- Per task: branch `task/<phase>-<task-id>` from `preview`.
- Parallel tasks get a worktree each: `git worktree add ../<repo>-wt-<task-id> -b task/<phase>-<task-id> preview`. Pass the absolute path to the builder; every command it runs is `cd <path> && <cmd>`.
- Sequential tasks: branch in the main checkout, no worktree needed.

## Step 3: Run batches

For each batch, spawn one builder subagent per task (in parallel within the batch, in the background, with the chosen builder model). Give each builder ONLY:

1. Its task card, worktree or branch, and doc paths to read (not the whole planning folder)
2. The relevant T-xxx rows from `04-test-spec.md`
3. These rules, verbatim:

> **Builder rules**
> - Touch only your owned files. Need a shared file changed? Put the exact change in your report.
> - Write the tests for your T-xxx first, from the test spec wording, then implement until they pass.
> - Comments only point to other files or docs (`See planning/decisions.md#D-004`, `See src/lib/x.ts`). No comments that justify choices, claim correctness or describe expected behaviour. No TODO without a task ID.
> - Run the Verify command. Everything must be green before you commit.
> - Commit at least once per task: `<type>(<task-id>): <summary>` (conventional commits). Never commit `.env*`.
> - Report in at most 12 lines: files changed, tests added (T-xxx), verify result, shared-file requests, blockers. No code in the report.

While builders run, keep your own context small: do not open their files.

## Step 4: Verify gate (per task)

Spawn a **fresh verifier** per finished task (verifier model). It is blind: give it the task ID, branch or worktree path, the doc paths and the T-xxx list. **Do not give it the builder's report.**

Verifier instructions:

> **White-box review** (read-only on code; may run commands):
> - Read the task's PRD sections, design.md (UI tasks), decisions.md and the T-xxx rows, then the code on the branch (`git diff preview...<branch>`).
> - Judge the code against the docs only. Check: acceptance criteria met, tests really test the T-xxx behaviour (not tautologies), security and permission rules, design tokens used (no hard-coded colours), file ownership respected, no secrets, comment policy respected.
> - Run lint, typecheck, tests and build yourself.
>
> **Browser test** (only if the user allowed it and the task has a UI change):
> - Start the app, use mock data or `.env.local` credentials only.
> - Walk through each browser T-xxx.
> - Screenshot the full page **before** (on `preview`) and **after** (on the task branch) for every changed screen. Save to `planning/evidence/<task-id>/before-<screen>.png` and `after-<screen>.png`.
>
> **Report** (max 20 lines): `VERDICT: PASS | FAIL`, a line per T-xxx (pass/fail), issues as `file:line: problem (doc reference)`, screenshot paths.

## Step 5: Merge or fix

- **PASS**: in the main checkout, `git checkout preview && git merge --no-ff task/<phase>-<task-id>`, apply any shared-file requests (commit them), remove the worktree, delete the branch. Tick the T-xxx in `04-test-spec.md`, update `progress.md`.
- **FAIL**: write a fix card from the verifier's issues and send it to a builder (new subagent, same branch). Re-verify with a fresh verifier. After 2 failed fix rounds, stop and ask the user. Log what went wrong in `planning/ai-log.md`.
- For UI tasks, show the user the after screenshots in your reply (attach or display them if the surface allows, otherwise give the paths) so they can see the change without running the app.

## Step 6: Phase end

On `preview`: run the full lint, typecheck, test and build. Spawn a fresh verifier for a phase-level regression pass (all T-xxx of the phase, browser flows if allowed, screenshots of key screens). Fix before starting the next phase. Update `progress.md` with a phase summary.

## Step 7: Finish

When every MVP feature in the PRD is done and its T-xxx are ticked:

1. Final full verification on `preview` (fresh verifier, all tests, browser walk-through with screenshots).
2. Write `planning/release-notes.md`: what was built (F-xxx), test checklist status, known gaps, what was cut, weakest part, suggested next steps.
3. Open a PR `preview -> main` with `gh pr create`, body = release notes summary.
4. **Ask the user before merging to main.** Merging is production; never merge it on your own.
5. Reply with: what changed, test pass count, screenshots of key screens, the PR link.

## Context and session hygiene

- Your context is the scarce resource. Delegate reading; accept short reports only.
- After every batch, update `progress.md` so a fresh session can resume.
- If your context grows heavy or a phase ends, run **des-handoff** and suggest continuing in a fresh session with `/des-build`.
- Every correction you make to a subagent's work goes into `planning/ai-log.md` (what it did, what was wrong, how you fixed it).
