# Template: `docs/coordination/team-rules.md`

The rules every ticket session follows, read right after its own handoff. The coordinator writes and versions this file; each accepted team-wide ruling is edited in here the day it's made. Keep it to rules a session needs while working; the coordinator's own procedures belong in `coordinator.md`.

Each section below names what it must settle. Fill it in, or delete the section if the project has nothing to say. Copy below the line.

---

```markdown
# Rules for every ticket session (<project>)

Read this after your ticket's handoff. The handoff wins where they differ.

## Who you are

You execute one ticket in your own worktree and branch, named in your handoff. The coordinating session is `<name>`, in `<main checkout>` on `main`; find it with `ListAgents` and reach it with `SendMessage`. Send it: cross-ticket questions, "a task landed that another ticket relies on", "PR opened", "merged", and anything about a shared resource. Ask rulings only the user can give in your own terminal; the user watches it.

## Before anything

1. `git fetch origin && git merge origin/main`, then `<install command>`.
2. Reconcile every name and line the plan cites against `main` as it is now; note drift in your first commit message or the PR.
3. `<baseline check>` green before Task 1.
4. Read `AGENTS.md`<, `KNOWLEDGE.md`> and the plan's Decisions section in full.

## How to execute

- Models: <default implementer> for routine tasks; <stronger model> only for tasks the plan marks hard. <Models never to use, and why.>
- Effort: execution at `<effort>`, and every subagent spawned with that effort. A running session never switches model or effort.
- Parallelism: independent tasks on <the cheaper model> may run at once, up to <n>, each in its own subagent worktree; tasks on <the stronger model> run one at a time. A task small enough to do inline is done inline. While another session holds the heavy lock, run one implementer at a time.
- Reviews per task: one reviewer, which spawns no subagents; at most one re-review, and only when a fix changed behavior.
- Commit after each task passes review; push after each commit.
- Shut down finished subagents. Remove each subagent worktree once its branch is merged into yours (`git worktree remove <path>`, then `git branch -d <branch>`).

## After the last task, in this order

1. Open a draft PR (`pull-request-creator` skill). Tell the coordinator the number.
2. <The review skills, in order, each read fresh from its own SKILL.md, never from a summary.>
3. Reply on the PR to every comment: adopted with the commit, or why not.

Marking the PR ready and merging happen only on <the user's / the coordinator's> say.

## Checks

- Locally, run only what your change affects: `<affected-only command>`.
- The gate before merge: merge `origin/main`, run `<gate command>`, paste its summary in the PR body.
- <When CI runs, and that sessions never add a workflow or job.>

## Shared machine

- Heavy runs (<list>) take the lock first: `until mkdir /tmp/<project>-heavy.lock 2>/dev/null; do sleep 15; done`, and `rmdir /tmp/<project>-heavy.lock` when the run ends, pass or fail.
- Run tests in the foreground. If a run would pass the tool timeout, split it.
- <Shared resources: who may touch them, ask the coordinator before <commands>, and how to free one when done.>
- Never `cd` into another worktree; read it with `git -C <path>`.

## Rules that bite

- No new environment variable, no GitHub issue, no destructive git or data operation, no secret tooling without the user's explicit yes in your own conversation. Your handoff lists what is already approved. Hand blocked commands to the user as `! <cmd>`.
- <Files never to read or print.>
- <Domain terms from `KNOWLEDGE.md` that sessions get wrong.>
- <Generated-not-handwritten artifacts, e.g. migrations, and the exact command.>
```
