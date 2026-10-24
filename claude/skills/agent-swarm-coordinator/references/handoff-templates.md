# Handoff templates

A handoff is a ticket session's whole prompt. It lives in `.handoffs/` (gitignored), one file per ticket and phase: `handoff-ticket-<n>-plan.md`, `handoff-ticket-<n>.md`. It carries what is specific to this ticket and this moment, and points at everything else: team rules, plans, skills, decision records. Under ~60 lines.

Before writing one:

- Check every statement about external state (an app installed, a key set, a branch merged) read-only, or mark it "unverified".
- Name skills by path and tell the session to read them fresh. Don't summarize their steps: summaries go stale.
- Copy the user's rulings verbatim, with their date.

## Planning

```markdown
# Planning handoff: ticket <n>, <title> (#<issue>)

You write the plan for ticket <n>. You do not execute any task. The coordinator is `<name>` in `<main checkout>` on `main`; reach it with `SendMessage` (check the name with `ListAgents` if a send fails).

- Worktree `<path>`, branch `<branch>`, cut from `main` at <sha>. Never `cd` into another worktree; read other branches with `git show origin/<branch>:<path>`.
- Plan file: `<path>`, written with `<planning skill>`. <Roadmap row / wave table updates.>

## Decided: plan it, don't reopen it

<The user's rulings, verbatim, dated. Approved env vars, if any, with their exact shape.>

## Read first

1. `AGENTS.md`<, `KNOWLEDGE.md`>.
2. <Decision records, prior tickets' code, other branches' plans this one touches.>

## What the plan must contain

- "Interfaces this plan calls", with file:line.
- Tasks in order, each marked hard (<stronger model>) or not (<default model>). Split any task expected to run over ~45 min.
- A Decisions list only for what the rulings leave open, each with a recommended option.
- "What later tickets rely on".
- The local checks per task.
- While planning, don't touch shared resources (<list>).

## Review

<Self-review, and any second-opinion pass, by skill path, read fresh. What to do if the pass is blocked: send the coordinator the exact error; don't switch models.>

## When the plan is done

- Commit and push `<branch>`. No PR.
- `SendMessage` the coordinator: the SHA, the task list with models, the open Decisions with recommendations, risks. Short: the user reads it as a numbered list.

## Standing rules

See `docs/coordination/team-rules.md`, "Rules that bite".
```

## Execution

```markdown
# Execution handoff: ticket <n>, <title> (#<issue>)

Read `docs/coordination/team-rules.md` next. The coordinator is `<name>` (check with `ListAgents`).

- Worktree `<path>`, branch `<branch>` (plan <sha>; merge `origin/main` first, it has moved to <sha> or later).
- Plan: `<path>`, Tasks <range>. Models and parallel groups as the plan marks them<: …>.
- <Order relative to other tickets: prerequisites vs merge points, and who integrates if both touch the same code.>
- PR body ends `Closes #<issue>`.

## Rulings (the user, <date>)

<The answers to the plan's Decisions, verbatim. Approved env vars. Anything the user does hands-on, and when.>

## Shared resources

<Which ones this ticket may need; ask the coordinator before <commands>. Who else is running alongside.>

## What the coordinator needs from you

A `SendMessage` when <task 0 is done (what drifted)>, when <an interface another ticket depends on lands>, before <any user hands-on step>, when the draft PR is open, and when the reviews are answered.
```

## Coordinator succession

When the coordinator role moves to a new session (context full, machine change, end of day):

```markdown
# Handoff: <project> coordinator

You are the coordinating session for <project>. Load the `agent-swarm-coordinator` skill, then read `docs/coordination/coordinator.md` and `team-rules.md`. Run in `<main checkout>` on `main`.

## Sessions

| Ticket | Session name | Worktree / branch | State | Waiting on |
| ------ | ------------ | ----------------- | ----- | ---------- |

## Open asks to the user

<Each one quoted from the session's transcript, with where to answer it.>

## Shared resources

<Who holds each one right now.>

## Spend so far

<Ledger total and the query, with the time it was read.>

## Delegations in force

<What the user has delegated, verbatim, with the date.>

## First steps

1. List live sessions and read each one's latest message from its transcript.
2. Recreate the heartbeat and the idle subscriptions.
3. Run the worktree sweep.
```

Then the outgoing coordinator stops acting: one coordinator at a time.
