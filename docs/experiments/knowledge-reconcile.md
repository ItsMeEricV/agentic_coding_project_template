# Experiment log: keeping KNOWLEDGE.md current via hook + command

> **This is a status/notes log, not instructions.** Nothing here is a rule to
> follow. The active behavior lives in `hooks/knowledge-reconcile.sh`,
> `commands/update-knowledge.md`, and the README hook table. This file records
> _why_ those look the way they do and what's still open, so we don't re-litigate
> decisions in a later session. Update it when the experiment moves.

**Status:** experimental, live (symlinked into `~/.claude/`). Tracked in PR #22
(`ev-knowledge-reconcile-hook`).

## The problem

`KNOWLEDGE.md` drifts because keeping it current depends on the agent updating it
inline or the user remembering to ask — both get skipped. The two obvious fixes
each fail on their own:

- A full glossary review at the end of every run is too heavyweight.
- A manual `/update-knowledge` slash command is too easy to forget.

Goal: a compromise that fires **only when there's plausibly something to record**,
mechanically (can't be forgotten) but cheaply (doesn't churn for nothing).

## What we built

| Piece                             | Role                                                                                                                            |
| --------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| `commands/update-knowledge.md`    | **Single source of truth** for the reconcile procedure. User runs `/update-knowledge`; the hook points here.                    |
| `hooks/knowledge-reconcile.sh`    | `Stop` hook. Cheap detection + loop guards. Blocks once and points the agent at the command — no duplicated steps.              |
| `knowledge-reconcile:skip` marker | Shipped in the template `KNOWLEDGE.md`; the hook skips any glossary still carrying it. Deleted when a project seeds real terms. |
| README wiring                     | Symlink `commands/` into `~/.claude/`, register the `Stop` hook in `settings.json`.                                             |

**No duplication:** the hook never restates the procedure; its block `reason`
references `commands/update-knowledge.md`. The command file is the only place the
steps live; the user path (`/update-knowledge`) and the hook path consume it.

## Design decisions (and what we rejected)

- **`Stop` hook, not `SessionEnd`.** Only `Stop` can block completion and inject
  an instruction back into the model; `SessionEnd` is observability-only.
- **Block-once with an escape hatch**, not a soft non-blocking reminder. The block
  is the only way to force the action, but the `reason` always offers "if there's
  nothing to record, say so and stop" so it can't wedge a session. Loop-safe via
  `stop_hook_active` + a once-per-session marker file.
- **Hook + command share logic via a pointer**, not by copying the procedure.
- **Considered and shelved:** demoting to a deferred next-session reminder (option
  "C") — never interrupts, but too weak/ignorable. Kept blocking instead.

## Detection: evolution

**v1 — lexical (rejected).** Grep the transcript for cue phrases (`call it`,
`the term`, `rename`, `disambiguate`, …). Too eager: a pure UI/bugfix session that
merely _mentioned_ domain nouns ("Class", "Collection") tripped a cue and forced a
full multi-file reconcile that found nothing — ~12 minutes of churn for zero edits.
That real false positive is what killed v1.

**v2 — git-diff domain-type signal (current).** Fire only when the **branch diff**
adds a PascalCase `type` / `interface` / `enum` / Prisma `model` / Zod schema whose
name appears in **no** `KNOWLEDGE*.md`. Keys off durable artifacts, not phrasing, so
a session that introduces no new type stays silent. Details:

- Diffs `base..worktree` (`merge-base HEAD main/master` → working tree) so a type
  added in an earlier branch commit still counts; degrades to uncommitted-vs-`HEAD`
  on the default branch.
- Extracts declared names from added lines only; strips common **implementation
  suffixes** (`Props`, `State`, `Args`, `Input`, `Output`, `Response`, `Request`,
  `Dto`, `Config`, `Options`, `Context`, `Provider`, `Handler`, `Params`, `Ref`,
  `Event`, `Error`).
- Keeps only names absent from every `KNOWLEDGE*.md`, then names them in the nudge.
- **Silent-on-empty:** the nudge tells the agent to make no edits and no summary if
  the types turn out to be plumbing — no reconciliation table.

**Suppression guards (all must pass to fire):** glossary exists; not the unseeded
template (`knowledge-reconcile:skip`); a new undocumented domain-type name in the
diff; no `KNOWLEDGE*.md` already edited this session; not already nudged this
session; not inside a `stop_hook_active` continuation.

## Tuning ledger

**Resolved**

- Unseeded template glossary fired on itself → skip marker. ✅
- Lexical over-firing on UI/bugfix sessions → replaced by the diff signal. ✅

**Open**

- **Stack-specific extraction.** Regexes assume TS / Prisma. Python, Go, Rust, etc.
  won't trigger until their declaration patterns are added.
- **Technical-but-not-domain types.** A genuinely new type that's infrastructural
  (e.g. `RetryPolicy`) can still fire. Now cheap — a named check with a clean
  "nothing to add, stopping" exit, not a 12-minute churn — so judged acceptable.
- **Meta-tooling sessions in a seeded repo.** A session _about_ glossaries in a repo
  whose marker is already deleted could still false-fire. Rare and low-cost; left
  unaddressed.

## Where to look / how to tune

- Add/remove implementation suffixes or declaration patterns: `hooks/knowledge-reconcile.sh`.
- Change the reconcile procedure: `commands/update-knowledge.md` (single source).
- Re-enable/adjust the marker behavior: the `knowledge-reconcile:skip` grep in the hook.
