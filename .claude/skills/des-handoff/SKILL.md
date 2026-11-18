---
name: "des-handoff"
description: "Write a compact handoff file from the current session so a fresh session can continue with only the context it needs. Use when a session is long, at phase ends, or /des-handoff."
---

# des-handoff: pass the baton

Goal: a fresh session reads one file and continues as if it had been here, without the noise of this chat. Keep only what the next session needs to act; link to docs instead of copying them.

## Step 1: Gather (from this chat and the repo)

- `git status`, current branch, `git log --oneline -10`, open worktrees (`git worktree list`)
- Last test, lint and build results (run the quick checks if unknown)
- From the conversation: the goal, what was done, what is half-done, decisions made and why, things the user asked for or ruled out, preferences they stated, dead ends tried, open questions

## Step 2: Write the handoff

Path: `planning/handoffs/YYYY-MM-DD-HHMM-<slug>.md` (if there is no `planning/`, use `HANDOFF.md` in the repo root). Aim for under 150 lines. No em dashes.

```markdown
# Handoff: <slug>
Date: <date>   Branch: <branch>   Last commit: <sha> <message>

## Goal
One or two lines: what we are trying to achieve right now.

## State
- Done: ...
- In progress: ... (file, what is left)
- Not started: ...
- Checks: lint ok / typecheck ok / tests 41 pass 2 fail (names) / build ok

## Decisions this session
- D-xxx or short line: decision, why, rejected option (log big ones in planning/decisions.md)

## User said
Preferences, constraints and rulings from the user that are not in the docs yet.

## Gotchas and dead ends
What failed and why, so it is not retried.

## Open questions
Things needing the user's answer.

## Next steps
1. ...
2. ...

## Read first
- planning/progress.md
- <only the doc sections and files the next step needs>

## Resume prompt
> Paste this into a fresh session:
> Read planning/handoffs/<this file> and the files under "Read first". Then <next step 1>. Use /des-build if continuing the build.
```

## Step 3: Update and save

1. Update `planning/progress.md` to match the State section (if it exists).
2. Move any decision the user confirmed into `planning/decisions.md`, and any AI mistake into `planning/ai-log.md`.
3. Commit only the handoff and planning files: `docs(handoff): <slug>`. Never commit other uncommitted work as part of a handoff; list it under In progress instead.

## Rules

- Facts only. Mark guesses as `Assumption:`.
- Never include secrets, tokens, credentials or `.env` values.
- No long code or raw logs; reference `file:line` instead.
- Reply to the user with the file path and the resume prompt, nothing else.
