# The project's half: contract and template

The skill holds what is true for any repo. The project holds what only it knows, in two committed docs:

- `docs/coordination/coordinator.md`: the coordinator's half (this template).
- `docs/coordination/team-rules.md`: every ticket session's rules (`team-rules-template.md`).

Another path is fine if `AGENTS.md` names it. Together with the skill they must answer every question below; a gap means the coordinator guesses.

## The contract

| #   | The project must say                                                                                                                             | Required              | The skill's default when absent                                                                 |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------- | ----------------------------------------------------------------------------------------------- |
| 1   | Where the roadmap, plans, and decision records live                                                                                              | yes                   | —                                                                                               |
| 2   | Worktree path and branch naming; where the coordinator runs                                                                                      | no                    | sibling `<repo>-<topic>` on `<user prefix>-<topic>`; coordinator in the main checkout on `main` |
| 3   | Where handoffs live and which templates they start from                                                                                          | no                    | `.handoffs/` (gitignored), `handoff-templates.md`                                               |
| 4   | Machine caps: live ticket sessions, subagent worktrees per session                                                                               | yes                   | 3 subagent worktrees per session; no default for sessions                                       |
| 5   | The heavy-run lock path and which commands count as heavy                                                                                        | yes                   | —                                                                                               |
| 6   | Single-owner resources (local stack, signed-in browser, shared daemon): how to tell who holds one, and how to move it with no step from the user | when any exist        | —                                                                                               |
| 7   | That every lint/test/typecheck/format config ignores `.claude/`                                                                                  | yes                   | —                                                                                               |
| 8   | The spend ledger (the query), each vendor's meter (MCP or CLI call) and caps; what counts as a paid run; the per-run cap                         | when anything is paid | $3 per run                                                                                      |
| 9   | The merge gate: the command, where its summary goes, who runs the full check on main and when, branch-protection quirks                          | yes                   | affected-only check on the branch merged with main; full check on main after merges             |
| 10  | The review order for ticket PRs                                                                                                                  | no                    | draft PR → the project's review skills → reply on the PR                                        |
| 11  | What the user has delegated to the coordinator beyond the skill's table                                                                          | no                    | the skill's table                                                                               |
| 12  | Steps only the user can do                                                                                                                       | yes                   | —                                                                                               |

Team rules carry the rest of what a ticket session needs (`team-rules-template.md`).

Rules of thumb for both docs:

- **Facts and commands, not narrative.** A ruling gets its date and one line of why; the war story stays in memory or git.
- **Edit in place.** A new ruling replaces the old line; don't append a correction below it.
- **Never restate a skill.** Point at it by name. A stale copy outlives the skill.
- **Under ~80 lines each.** Past that, split by area and link.

## Template: `docs/coordination/coordinator.md`

Copy below the line. Replace every `<…>`; delete a section only when the contract row says it can be absent.

---

```markdown
# Coordinating <project>'s ticket sessions

The <project> half of the coordinator's job; the generic half is the `agent-swarm-coordinator` skill. Ticket sessions follow [team-rules.md](team-rules.md).

## Where things are

- Roadmap: `<path>`. Plans: `<dir>`. Decisions: `<dir>`.
- Handoffs: `.handoffs/<wave>/handoff-ticket-<n>[-plan].md`, from the skill's templates, pointing at `docs/coordination/team-rules.md`.
- Worktrees: `<parent dir>/<repo>-<topic>`, branch `<prefix>-<topic>`. The coordinator runs in `<main checkout>` on `main`.

## Machine

- Caps on this machine (<RAM>, <what else is resident, e.g. a container VM of N GB>): at most <n> live ticket sessions, <n> subagent worktrees per session.
- Heavy runs take `/tmp/<project>-heavy.lock` first: <list the commands>.
- Every walking tool ignores `.claude/`: <list the configs that carry the ignore>.

## Shared resources

- <resource>: one holder at a time. Who holds it: `<read-only command>`. Moving it: <the steps the receiving session runs itself>. The user never <signs in again / approves a prompt> for a move, because <why it's safe>.

## Spend

- Ledger: `<query>`. Vendor meters: `<MCP or CLI call>`. Vendor caps: <key, cap, the exact refusal text>.
- Paid runs: <what counts>. Cap per run: $<n>; halt at the first loop sign.

## Merges and CI

- Gate: `<command>` on the branch merged with `main`, its summary pasted in the PR body.
- After merges: the coordinator runs `<full check>` on `main` in the main checkout, under the heavy lock.
- CI and Git-connected integrations: <what one push triggers, who starts it, what it costs>. Branch protection: <quirks, e.g. PRs only, even for fixtures>.

## Delegated to the coordinator

- <anything beyond the skill's table, with the date the user said so>

## Things only the user does

- <commands and dashboards that need the user's identity, a passkey, a browser, or a paid plan>
```
