---
name: "des-plan"
description: "Start of the des pipeline: turn an idea into locked planning docs (brief, PRD, design, tech stack, test spec, logs, AGENTS.md, hooks). Use when starting any new project or /des-plan."
---

# des-plan: idea to locked planning docs

Pipeline: **des-plan** (this) -> **des-build** (orchestrated build + verification) -> **des-handoff** (any time a session gets long).

Goal: leave the repo in a state where any agent, in any fresh session, can build the project correctly by reading files only. Nothing important may live only in chat.

## Output

```
planning/
  00-brief.md         idea, users, problem, non-goals
  01-prd.md           features F-xxx, user stories, acceptance criteria, scope tiers
  02-design.md        design system and branding (UI projects only)
  03-tech-stack.md    stack, versions, why, what was rejected
  04-test-spec.md     tests T-xxx written from the PRD, as a checklist
  decisions.md        decision log D-xxx
  progress.md         current state, one screen max
  ai-log.md           where AI went wrong and how it was corrected
  handoffs/
AGENTS.md             short operating manual for any coding agent
CLAUDE.md             imports AGENTS.md plus Claude Code specifics
.claude/settings.json permissions + hooks
.claude/hooks/        hook scripts
.gitignore, .env.example
```

## Rules for the whole skill

- Ask with AskUserQuestion: at most 4 questions per round, recommended option first, only questions whose answer changes what you write.
- Each phase ends with a **gate**: show a short summary, get the user's OK, then mark the doc `Status: Locked` at the top. Never silently rewrite a locked doc; propose changes and log them in decisions.md.
- Facts that change over time (library versions, pricing, API shapes) are looked up, not recalled.
- Docs are concise: tables and lists over prose, stable IDs (F-001, T-001, D-001), no filler.
- No em dashes in any doc.

## Step 0: Resume check

If `planning/` exists, read `planning/progress.md` and resume at the first missing or unlocked doc. If no git repo exists, ask before running `git init`.

## Step 1: Ideation -> 00-brief.md

Interview in rounds. Challenge the idea honestly: is the problem real, what is the simplest version that proves it, what can be cut, what already exists.

Template:
- One-line pitch
- Problem and who has it
- Users and roles (with permissions if more than one role)
- Core loop: the 3 to 6 steps a user repeats
- Success: how we know it works (measurable)
- Non-goals and cut list
- Risks and open questions
- Constraints: deadline, budget, hosting, must-use tech

Gate: user confirms the brief.

## Step 2: PRD -> 01-prd.md (main agent, needs judgement)

The PRD comes before design and stack, so both are chosen to serve the features, not the other way round.

- Features as F-001, F-002 ... each with: user story, acceptance criteria (testable, numbered F-001.1, F-001.2), priority tier
- Scope tiers: **MVP** / **v1** / **Later**, plus an explicit **Cut list** with one-line reasons
- Non-functional: security, permissions, performance targets, data handling
- Data model sketch and key flows (diagram in Mermaid if it has branches)
- Out of scope

Gate: user confirms. Keep a running list of decisions made (context, decision, rejected options, why); they are written to decisions.md in Step 5.

## Step 3: Design and tech stack (parallel drafts)

First ask the user what only they can answer: design direction (mood, references, existing brand), stack preferences or constraints, hosting.

Then spawn two subagents **in parallel** (independent, no shared files). Each reads only `00-brief.md` and `01-prd.md` plus the user's answers you pass in, and returns its draft:

- **Design subagent -> 02-design.md** (skip if no UI): brand personality, colour tokens (with light and dark), type scale, spacing scale, radius, components list with states (covering every screen the PRD needs), layout rules, accessibility rules (contrast, focus, motion).
- **Stack subagent -> 03-tech-stack.md**: each layer with chosen tool, current stable version (looked up), why it fits the PRD, rejected alternatives, commands (install, dev, lint, typecheck, test, build), env vars needed (names only).

Review both, fix anything that contradicts the brief or PRD, then gate with the user. Add their choices to the running decisions list.

## Step 4: Test spec -> 04-test-spec.md (blind subagent)

Spawn ONE subagent that may read only `01-prd.md` and `02-design.md`. It must not read any code or the tech stack internals, so tests describe behaviour, not implementation.

It writes:

```
| ID | Feature | Type | Given / When / Then | Status |
| T-001 | F-001.1 | unit/integration/e2e/browser | ... | [ ] |
```

Requirements: every acceptance criterion has at least one test; include negative, permission and security cases; browser tests name the page and the visible result. This file is the merge checklist for des-build.

Main agent checks coverage (every F-xxx.n mapped), then gates with the user.

## Step 5: Project logs -> decisions.md, progress.md, ai-log.md, handoffs/

- **decisions.md**: write every decision from the running list as D-001, D-002 ... with: date, context, decision, rejected options, why, link to the doc section it affects. Add the D-xxx IDs back into the PRD, design and stack docs where relevant.
- **progress.md**: one screen max. Current phase (planning done), docs and their status, MVP feature count, test count, next step (run des-build), open questions.
- **ai-log.md**: table `| Date | Phase | What the AI did | What was wrong | How it was corrected |`. Add any corrections already made during planning.
- **handoffs/**: create the folder with a one-line README: handoff files are written by des-handoff, newest first.

## Step 6: Agent context -> AGENTS.md and CLAUDE.md

AGENTS.md, under about 80 lines, a map not an encyclopedia:
- What the project is (one line)
- Commands: install, dev, lint, typecheck, test, build
- Repo map: folder -> purpose
- Hard rules specific to this project (the things an agent would get wrong)
- Comment policy (copy exactly):
  > Comments only point to other files or docs, e.g. `See planning/decisions.md#D-004` or `See src/lib/auth.ts`. No comments that justify a choice, claim correctness, or describe expected behaviour. The reviewer must judge code against the docs without the builder's framing.
- Git workflow: `main` = production, `preview` = integration; task branches `task/<phase>-<task-id>` off `preview`; commit per task; never commit `.env*` except `.env.example`
- Where to read before working: `planning/progress.md`, latest file in `planning/handoffs/`
- Definition of done: lint, typecheck, tests and build green; mapped T-xxx ticked; verifier PASS

CLAUDE.md: first line `@AGENTS.md`, then only Claude Code specifics (skills to use: des-build, des-handoff).

## Step 7: Guardrails -> .claude/settings.json and hooks

Propose, show the user, then write (hooks run shell commands on their machine):

- **permissions.deny**: reading or editing `.env*` (except `.env.example`), `rm -rf`, `git push --force`, `git push origin main`
- **PreToolUse (Edit|Write)**: `.claude/hooks/protect.sh` blocks edits to `.env*` and to `planning/04-test-spec.md` expected results (exit 2 with a reason)
- **PostToolUse (Edit|Write)**: `.claude/hooks/lint-file.sh` runs the fast linter or formatter on the edited file only
- **Stop**: `.claude/hooks/quick-check.sh` runs the fast unit tests; keep it under about 30 seconds
- **SessionStart**: print `planning/progress.md`

Scripts read the tool input JSON from stdin with `jq`, are `chmod +x`, and use `${CLAUDE_PROJECT_DIR}` paths. Also write `.gitignore` (with `.env*`, `!.env.example`) and `.env.example` with names only.

## Step 8: Close

1. Make sure `progress.md` reflects the final state of planning
2. Commit on `main`: `chore(plan): lock planning docs`
3. Reply with: the doc list, the MVP feature count, test count, and the next step: run **des-build**
