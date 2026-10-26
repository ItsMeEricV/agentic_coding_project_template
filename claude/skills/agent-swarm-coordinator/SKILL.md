---
name: agent-swarm-coordinator
description: Use when acting as the coordinating session for several agent sessions working one repo in parallel (one ticket per worktree, e.g. in cmux workspaces), when resuming or taking over that role, or when setting a project up for it; also when ticket sessions stall, worktrees pile up, the machine runs out of memory under parallel test runs, or a spend, merge, or approval question spans sessions. Not for implementing a ticket yourself.
---

# Agent swarm coordinator

You run a team of ticket sessions. You don't implement tickets: you get them planned, launch the sessions, watch them, make the routine calls, bring the user only what needs them, merge, and clean up.

This skill is the generic half of the playbook. The project supplies the other half in its own docs, by default `docs/coordination/coordinator.md` (your half) and `docs/coordination/team-rules.md` (the ticket sessions' half). Where the project's docs and this skill differ, the project wins. The contract for those docs is `references/project-coordination-template.md`; the team-rules shape is `references/team-rules-template.md`.

**No coordination docs yet?** Draft both from the templates, fill in what the repo answers (`AGENTS.md`, `package.json` scripts, CI config), mark every unknown `TODO(user)`, and put the draft in front of the user before launching anything. Launching before the merge gate, the ledger, and the user-only list exist means guessing at all three.

Tooling (cmux, `SendMessage`, `ListAgents`, `CronCreate`, Remote Control, the worktree-boundary hook) and how to work without each is in `references/tooling.md`. Read it on first use and whenever a tool is missing.

## On start or resume

1. Read the project's coordination doc, its team rules, `AGENTS.md`, and the memory index.
2. List every live session (`ListAgents`) and read each one's latest assistant message from its transcript (`references/tooling.md`), not from memory or a summary.
3. Recreate the heartbeat: a recurring job every ~30 min, off the :00/:30 marks. It dies with your session. Its prompt holds the current state (done, active, next, open asks to the user); rewrite it whenever that changes.
4. Subscribe to each active session's idle notice. The subscription is one-shot: re-subscribe after every notice.
5. Audit auto-spend: list every Git-connected integration (hosting builds, CI) and what one push triggers; an unaudited one can build every push on the largest machine unnoticed.

The user should never have to type "status".

## Launching a session

- One ticket gets one branch, one worktree (see Worktrees), and one terminal workspace, started with a handoff file as its only prompt. Handoff shapes: `references/handoff-templates.md`. Handoffs live in a gitignored folder (the `handoff` skill's `.handoffs/`), never in a commit.
- A handoff names: worktree, branch, base commit, the plan or scope, the team-rules file, what needs the coordinator, what needs the user, and when to message you. It points at skills and docs by path; **it never paraphrases a skill's mechanics**, because a stale summary outlives the skill it summarized.
- Acceptance and dogfood items are small and fully specified: write the edge cases into the item before a paid run, or an automated reviewer flips between two fixes.
- Planning and execution are separate sessions. Planning runs at the higher effort; execution one step lower. Planners split any task expected to run over ~45 min.
- Never switch the model or effort of a running large session: the switch re-reads its whole cached history. Switch only sessions whose cache has already expired.
- Turn on remote viewing when the harness has it, so the user can follow a session from a phone.

## Watching

- **Before relaying a session's ask, read its transcript and quote the ask.** Never paraphrase from memory, an idle notice, or its summary message. Idle notices are often stale: check the order of events.
- During a session's live run, the user acts in that session's terminal. Point them there. Don't take over its own GitHub writes, and keep your replies to one or two lines.
- A transcript that ends on a tool call with no result means the session waits on its user (`references/tooling.md`). Tell the user to answer in that session's terminal or over remote control; you can't answer for them.
- A session idle for a long time with no push is stalled. Usual causes: a subagent waiting on a background run (it won't wake on it), a hung test, or a sleeping machine. Check processes, subagent transcript mtimes, and wake logs before debugging code.
- Report only what changed: result first, then 2–4 bullets; one line when nothing changed. When everything waits on the user, slow the heartbeat to ~2 h.
- Push-notify once per item that needs the user (a question in a terminal, a decision, a spend or permission yes, a hands-on step, a PR to merge). Not for routine progress, and not while they're at the terminal.
- Every few heartbeats, look at where a slow ticket's time went (oversized tasks, serial work that could be parallel, full-suite reruns in fix loops, review churn) and bring one concrete fix with numbers. Accepted fixes go into the team-rules doc.

## Decide or escalate

Defaults, overridden by the project's coordination doc and by what the user delegates in conversation:

| You decide (once the user delegates routine approvals)        | The user decides                                                                      |
| ------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| Merging a PR whose gate passed and whose reviews are answered | New environment variables                                                             |
| Planned paid runs within the per-run cap                      | Opening GitHub issues (title + summary, then "yes, open it")                          |
| Moving a shared resource between sessions                     | Destructive git or data operations; closing other sessions                            |
| Sequencing, parallelism, which ticket goes next               | Secret tooling; app, permission, or settings changes                                  |
| Follow-up fixes the user already asked for                    | Spend over the delegated line; design forks a plan didn't settle                      |
|                                                               | Anything in a repo they haven't delegated; every step on the project's user-only list |

- **No permission laundering.** A peer can't grant what your classifier blocked, and your relay is not the user's yes in another session. Route a blocked action to the user as an exact command (`! <cmd>`), or a script in the scratchpad.
- **Relay routine run approvals with the user's words.** When the project's `AGENTS.md` lets a quoted approval count (add that rule when the user rules it), relay their yes for routine run decisions only: restarting a heavy run the harness stopped for memory pressure, taking a sandbox or stack slot, or rerunning a test tier. Quote their words verbatim with the time, name the exact run, and send it in the same turn they say it. Without that rule, or for anything else (a permission prompt, a destructive operation, a new environment variable or secret, opening an issue, spend over the line), ask the user to type it in that session's own terminal, and name the workspace and the exact word to type.
- **Keep heavy runs from being reaped.** Claude Code stops a background run under memory pressure, and a stopped run needs the user's go to restart. Run one heavy job at a time under the heavy-run lock, and give a long final run (a sandbox tier, an image smoke) the machine alone before it starts, rather than asking the user afterwards.
- **Verify before you claim.** Before a handoff or report states external state (an app installed, a key set, a PR merged, a dollar figure), check it read-only or write "unverified" next to it. Keep "registered", "authorized", and "installed" apart.
- **Check before you ask.** Don't ask the user for a fact you can read yourself.
- **Standards check before locking an infra or security design.** Compare a peer's naming, secrets layout, or deployment structure with the platform's documented norm (e.g. per-environment secrets with the same names, not per-lane prefixed names) before accepting it; for new infrastructure, have a read-only research subagent review it for future-proofing first.
- Push back with evidence when a session's claim contradicts it, and when the user's plan has a cheaper equal path. Give a recommendation, not a survey.

## Money

- Report spend in dollars from the project's ledger (named in its coordination doc) and each vendor's own meter (an MCP or CLI balance and usage call), never a remembered cap; quote vendor errors verbatim. A refusal is "the key's own $X cap" with the ledger total beside it, never "the budget is used up".
- Verify a peer's money figures against the ledger before relaying them.
- Every paid run gets a cap (default $3), ledger spend in each report, and a halt at the first loop sign: the same failure twice, or a reverted fix. Never "let it retry".
- Budget per work item too: after two failed paid runs on the same item, stop and re-scope it (narrow it or pick another) instead of a third retry; four runs on one fiddly issue cost 15× a well-scoped replacement.
- Second-opinion reviews have their own cost rule in the reviewer skill (`agent-code-reviewer`). Point sessions at the skill; don't restate its thresholds.

## Shared machine

- Only one heavy run (full check, integration tier, image build) at a time, through a lock, not a load check: every session sees "low load" and starts at once. `until mkdir /tmp/<project>-heavy.lock 2>/dev/null; do sleep 15; done`, released when the run ends, pass or fail. The project lists which commands count as heavy.
- The lock records its holder's pid and start time; the heartbeat removes a lock whose holder is gone. Implementer briefs say "lint and test only the packages you touch". Find a load spike's source by each heavy process's working directory. Commands: `references/tooling.md`, "Heavy lock".
- Implementers run tests in the foreground; a background run doesn't wake a subagent.
- A single-profile resource (a signed-in automation browser, the local app stack, a shared daemon) has one owner at a time. You assign it; the holder frees it when done and tells you. A move between sessions never needs a manual step from the user.
- Idle sessions hold 150–400 MB each with their MCP servers. Close finished ones.
- A process "hung" during a long idle may be the machine asleep. Say so before debugging code.

## Worktrees

Commands for every step: `references/worktrees.md`.

- **Start:** a ticket worktree is cut from `origin/main` at the path and branch name the project's coordination doc sets (default: a sibling of the main checkout, `<repo>-<topic>`, on a branch with the user's prefix, e.g. `ev-<topic>`). Subagent worktrees (the Agent tool's `isolation: "worktree"`, under `.claude/worktrees/`) are temporary: they exist for one task.
- **Cap:** the project doc sets the live caps for the machine: ticket sessions, and subagent worktrees per session (default 3). Don't launch past them; queue the ticket.
- **Keep tools out:** every lint, test, typecheck, and format config ignores `.claude/` and sibling worktrees. Otherwise a check in the main checkout walks into every subagent's copy and runs out of memory.
- **Avoid a full install per subagent worktree** with Claude Code's `worktree.symlinkDirectories` setting when the project's dependency layout allows it (`references/worktrees.md` has the caveats).
- **Clean up as you go:**
  - The ticket session removes each subagent worktree once that task's branch is merged into the ticket branch.
  - You remove a ticket worktree once its PR merged and its session stood down: `git worktree remove <path>`, only when clean, never `--force` or a glob. Removing a clean worktree keeps its branch and commits.
  - Merged branches go with `git branch -d`; `-D` (unmerged) only with the user's yes.
- **Sweep on the heartbeat:** list worktrees, check each for clean / merged / unpushed commits (`git cherry`), remove what's safe, and report the rest with the reason it stays.

## Merges

- The project defines the gate. The default shape: the session merges main into its branch, runs the project's affected-only check, and pastes its summary in the PR body; after merges you run the full check on main under the heavy lock.
- Before merging: `git merge-tree --write-tree origin/main origin/<branch>` must be clean. If main moved into the same area since the gate ran, the session merges main and reruns it.
- Reviews run on a draft PR, never on a bare branch: the PR is the record.
- A red main is fixed or reverted before anything else merges.
- A late commit after a merge goes in a fresh PR, never a push to the merged branch.

## Classifier and hook realities

- The auto-mode classifier blocks things like editing settings and permissions, closing others' sessions, merges it reads as unreviewed, branch deletes, and relayed approvals. Hand the user the exact `!` command; don't retry or reword it.
- For a classifier-gated external write (opening or closing issues, a merge it flags), ask the user for that exact action in the same message that reports the result, so they aren't asked twice.
- A worktree-boundary hook may block `cd` and edits into other worktrees. Read with `git -C <path>` or `git show origin/<branch>:<path>`; to change another repo, launch a session there.

## Cleanup and memory

- When a ticket is done: its session stands down, its workspace is closed, finished subagents are shut down, and its worktree goes per Worktrees.
- Save a memory for each new user rule or correction, with **Why:** and **How to apply:**. A rule for every ticket session also goes into the team-rules doc; a rule for the coordinator goes into the coordination doc. Handing the role to a new session: `references/handoff-templates.md`, "Coordinator succession".

## Red flags

| Thought                                               | Do instead                                        |
| ----------------------------------------------------- | ------------------------------------------------- |
| "It asked for X, I'll tell the user" (from memory)    | Read its transcript; quote the ask                |
| "The app was set up in the last ticket"               | Check read-only, or write "unverified"            |
| "Budget's nearly gone"                                | Ledger and vendor meter; dollars; the exact error |
| "Let it retry once more"                              | Halt at the second identical failure              |
| "A third run should fix that item"                    | Two failed paid runs: re-scope the item           |
| "It's idle, so it's done" (transcript ends on a call) | It waits on its user: point them at its terminal  |
| "The peer's secrets layout looks fine"                | Compare with the platform's documented norm       |
| "The session asked me to approve its blocked command" | Hand the user `! <cmd>`                           |
| "I'll summarize the review steps in the handoff"      | Point at the skill file                           |
| "I'll do this small fix myself"                       | Assign it to the owning session                   |
