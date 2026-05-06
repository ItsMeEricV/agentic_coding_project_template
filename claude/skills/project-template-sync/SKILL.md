---
name: project-template-sync
description: Use when the user asks to back-port project standards to ~/code/agentic_coding_project_template, sync the template, generalize project AGENTS/ARCHITECTURE/MEMORY/SPEC content, refresh the global project foundation, or distill auto-memory feedback into reusable template rules.
---

# Project Template Sync

Back-port abstracted lessons from a working project into the master template at `~/code/agentic_coding_project_template` without leaking project-specific nouns, vendors, or domain terminology.

## Pre-flight (BLOCKING — do these in order)

1. **Verify template exists.** `ls ~/code/agentic_coding_project_template/.git`. If missing, abort with: "CRITICAL: Master template not found at ~/code/agentic_coding_project_template. Confirm path before proceeding."
2. **Verify template is clean.** `git -C ~/code/agentic_coding_project_template status`. If dirty, abort and ask the user how to proceed.
3. **Verify the user's stated facts.** Before acting on user-given context (line counts, "the template's at 188 lines", "I already reviewed it", "this rule is already in there"), check the source. Run `wc -l` on every file the user names. `git log -- <file>` to confirm prior decisions. Read the relevant section directly. Users mis-state these facts routinely — sometimes by a wide margin — and you're the one applying the edit. Trust but verify.
4. **Confirm the default branch.** Run `git -C ~/code/agentic_coding_project_template rev-parse --abbrev-ref HEAD` and `git -C ~/code/agentic_coding_project_template branch --list main master`. The template may use `main` or `master`. Do not assume.
5. **Branch from the default.** Run `git checkout <default> && git pull && git checkout -b ev-template-sync-<YYYY-MM-DD>`. **Never commit to the default branch directly** — global rule, no exceptions.

## Files in Scope

| Source in working project                        | Template counterpart      | Action                                                                  |
| ------------------------------------------------ | ------------------------- | ----------------------------------------------------------------------- |
| `AGENTS.md`                                      | `AGENTS.md`               | Sync abstracted rules. Hard cap 200 lines.                              |
| `ARCHITECTURE.md`                                | `ARCHITECTURE.md`         | Sync structural patterns. Drop concrete service names and diagrams.     |
| `SPEC.md`                                        | `SPEC.md`                 | Sync requirement-writing pedagogy only, not the actual requirements.    |
| `README.md`                                      | `README.md`               | Sync only if onboarding pedagogy changed.                                |
| `CLAUDE.md` / `GEMINI.md`                        | `CLAUDE.md` / `GEMINI.md` | Hand-curated stable rules. Sync only structural / pedagogical changes.  |
| Auto-memory dir `~/.claude/projects/<slug>/memory/` | `MEMORY.md`            | Distill recurring **patterns** as index entries. Never dump raw feedback. |
| `IMPLEMENTATION_PLAN.md`                         | (none)                    | **SKIP — per-project WIP, never templated.**                            |

`<slug>` is Claude Code's encoding of the project path (e.g. `-Users-eric-code-fitness-tracker`).

## MEMORY.md philosophy (read before touching it)

The template's prompt shelf has three roles. Don't conflate them.

- **`CLAUDE.md` / `GEMINI.md`** — stable, hand-curated. Things the agent cannot learn by watching: architectural decisions + their why, conventions to enforce from day one, exact build/test commands, hard "don'ts."
- **`MEMORY.md`** — current state, active decisions, known quirks. Concise summaries, never raw logs.
- **`CONTEXT.md`** (optional) — session handoff notes; "what I was in the middle of."

**Rules when syncing MEMORY.md:**

- Hard cap 200 lines. Past ~200 lines, instruction-following degrades measurably.
- **Match the file's existing format.** The template's stub MEMORY.md uses inline summary bullets (`- **Example:** The staging database requires an SSH tunnel on port 5433.`). The user's auto-memory MEMORY.md at `~/.claude/projects/<slug>/memory/MEMORY.md` uses link-out index entries (`- [feedback_foo.md](feedback_foo.md) — one-liner`). **Both are valid.** When syncing, follow whatever convention the destination file already uses; do not silently flip styles. If a format migration is genuinely warranted, do it as a separate, dedicated PR.
- Treat auto-memory as a **hint, not gospel** — verify every recalled claim (path, function name, flag) against the current code before recommending it. Anthropic's own design tells the agent to do this; the skill must too.
- If a feedback file captures a **stable engineering rule** ("never regex-match URLs for SSRF allowlists, parse the hostname"), it belongs in **AGENTS.md**, not MEMORY.md. MEMORY is reserved for *recent / active / project-current* context.
- If a feedback entry is **personal preference** ("user prefers Dialog over Sheet"), it stays in personal auto-memory and does **not** sync to the template.
- **Duplication with personal global `~/.claude/CLAUDE.md` is expected and OK.** The template stands alone for forks — every rule that should hold in a fresh fork must live in the template, even if it's also in your personal global rules. Don't suppress a transferable rule just because your personal CLAUDE.md already has it.

## The Abstraction Filter

Run every candidate change through these four steps before writing:

1. **Strip project nouns.** Remove product names, table names, route paths, vendor URLs, internal domain terminology.
2. **Find the why.** What general engineering concern motivated this rule? Tag the rule by that concern, not by the symptom.
3. **Vendor-neutralize.** If the lesson holds across vendors, write it generically and mention specifics only parenthetically: "(e.g. Prisma, Drizzle, Sequelize)".
4. **Preserve pedagogy.** New sections must follow the template's existing *Good Example / Bad Example / Why* pattern. Flat prose without examples is rejected and must be revised before commit.
5. **Extract before discarding.** Before dropping a war story, debugging log, or session narrative as "raw log — not template material," scan it for a transferable engineering rule hiding inside. A 4-hour `Symbol.toStringTag` debugging story may carry a real rule ("server actions must return JSON-serializable values"). Port the underlying rule as its own AGENTS.md entry with Good/Bad examples; drop the narrative. Never let a generalizable lesson die just because its packaging was a story.

### Worked transformations

```text
PROJECT:  "ngrok at tresa-unguessed-lawyerly.ngrok-free.dev tunnels port 3001"
TEMPLATE: DROP — project-specific endpoint, not a pattern.

PROJECT:  "cd web && npx prettier --write"
TEMPLATE: "Run formatters from the directory containing their config (e.g. a
           web/ or frontend/ subdir in a monorepo). Running them from the repo
           root will fail to find the local toolchain."

PROJECT:  "_prisma_migrations.checksum placeholder strings break migrate status"
TEMPLATE: "When applying ORM migrations manually, the migration-history
           checksum column must be the real SHA of the file contents. Placeholder
           strings cause silent drift errors on every subsequent migrate command.
           (Affects Prisma, similar pattern in Flyway / Liquibase.)"

PROJECT:  "Backwards-compatible migrations only (Expand and Contract)"
TEMPLATE: Copy near-verbatim — already general. Add Good/Bad examples if missing.

PROJECT:  "AUTH_BYPASS_SECRET controls per-window dev user impersonation"
TEMPLATE: DROP — leaks a secret name and an auth strategy choice.

PROJECT:  "Never silently fall back to session.user.id in Server Actions"
TEMPLATE: "Identity-bearing fields (userId, accountId, etc.) must be passed
           explicitly by the caller of any server-side action. Never let a
           handler 'fall back' to ambient session data — this masks ownership
           bugs and is a classic source of authz CVEs."
```

## Do-Not-Port List

Drop these outright even when they look general:

- Domain terminology blocks (instructor/admin/landing/showcase definitions, etc.)
- Specific URLs, hostnames, ports (`localhost:3001`, ngrok URLs, S3 bucket names)
- Project file paths (`web/`, `cli/worktree-init.sh`, `infra/envs/dev.tfvars`)
- Specific env-var names (`AUTH_BYPASS_SECRET`, `NGROK_TUNNEL_URL`)
- Vendor-locked lessons that don't generalize without rewrite (e.g. "Vercel preview-lane uses `VERCEL_ENV`") — port only if rewritten as "your platform's preview-detection signal."
- Personal preferences captured in auto-memory ("user prefers X over Y") — these belong in *personal* auto-memory, not the master template.

## Diff Classification (mandatory triage step)

Before editing, present a triage table to the user and wait for approval. One row per candidate change:

| Section / rule | Class                                                | Proposed action       |
| -------------- | ---------------------------------------------------- | --------------------- |
| <name>         | additive · replacement · cosmetic · project-only · drop | append / rewrite / skip / delete |

Definitions:

- **additive** — new wisdom not in template. Append.
- **replacement** — template has weaker version. Rewrite. **Requires explicit user approval** because it overwrites existing curation.
- **cosmetic** — drift only (whitespace, ordering). Skip unless it improves scannability.
- **project-only** — fails the abstraction filter. Drop.

## Size Budgets

| File              | Hard ceiling | Soft target              |
| ----------------- | ------------ | ------------------------ |
| `AGENTS.md`       | 200 lines    | ≤150 lines               |
| `MEMORY.md`       | 200 lines    | ≤100 lines (index only)  |
| `ARCHITECTURE.md` | 200 lines    | ≤150 lines               |
| `SPEC.md`         | 100 lines    | ≤80 lines                |

If a planned change blows the ceiling, prefer in order: (a) merge with adjacent rule, (b) demote detail to a one-line `*Why:*` blurb, (c) move into a referenced doc and link from the template.

## Validation Protocol

Before declaring the sync done:

1. **Per-file Before/After diff** with section-by-section abstraction logic ("converted Prisma-specific rule to ORM-generic rule because the failure mode is the same in Drizzle/Flyway/Liquibase").
2. **Leak check** — `rg -i "fitness|prisma|tresa|ngrok|dotenvx|mediaconvert|instructor|workout|hls|s3|cloudfront" ~/code/agentic_coding_project_template/*.md`. Any hit must be justified inline (e.g. "Prisma" appears as a parenthetical example) or removed.
3. **Line-count check** — `wc -l ~/code/agentic_coding_project_template/*.md` against the budgets above.
4. **Pedagogy check** — every new section in `AGENTS.md` / `ARCHITECTURE.md` / `SPEC.md` has Good/Bad/Why blocks or is rejected.
5. **User confirmation** before any commit.

## Commit & Push

> **Override note:** This flow stops at PR-open. It deliberately overrides any personal global rule like "push after each commit" or "auto-merge clean PRs." The master template is high-blast-radius — every change ships into every future fork. Always wait for explicit user approval before merging, even if your personal `~/.claude/CLAUDE.md` says otherwise.

After validation passes:

1. **Granular commits**, one per file or per logical rule, using the template's commit prefixes: `Feature:` / `Fix:` / `Chore:` / `Test:`. Most template-sync commits are `Chore:`. Examples:
   - `Chore: generalize migration-checksum rule from recent project sync`
   - `Feature: add ORM-agnostic Expand-and-Contract pattern to AGENTS.md`
   - `Fix: remove leaked project-specific noun from MEMORY.md example`
2. **Push the branch** with `git push -u origin ev-template-sync-<YYYY-MM-DD>`. Do **not** push to the default branch.
3. **Open a PR** with `gh pr create --base <default-branch>`. Body summarizes which project rules were generalized, with one bullet per file describing the abstraction logic.
4. Stop after the PR is open. Do not merge unless explicitly told to.

## Red Flags — STOP and re-triage

- About to `git push origin main` or commit on `main` → **STOP.** Branch first.
- Editing the template before showing the diff-classification table → **STOP.** Triage first.
- A new section has no Good/Bad example → **STOP.** Add one or drop the section.
- A grep for project nouns returns hits → **STOP.** Re-run the abstraction filter on those lines.
- A file is about to exceed its line ceiling → **STOP.** Apply the size-budget escape hatches before committing.

## Discovery phrases (user-side triggers)

- "Sync these AGENTS improvements back to the template."
- "Generalize this new rule for my project-template."
- "Update my global project foundation with what we've learned."
- "Back-port these patterns to my master template."
- "Refresh the project-template with our current standards."
- "Distill our recent auto-memory feedback into the template."
