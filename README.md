# Agentic Coding Project Template 🛠️

> **What is this?** A drop-in foundation for AI-assisted coding projects. It bundles the markdown files agents read to understand your project, a set of Claude Code skills that automate common workflows, opinionated Docker dev stacks, and a few small scripts. Fork the relevant pieces into a new project, fill in the placeholders, and your coding agents arrive pre-briefed.

The repo has six halves, each independently useful:

| Pillar                | What it is                                                    | When you want it                       |
| --------------------- | ------------------------------------------------------------- | -------------------------------------- |
| 📋 **Prompt shelf**   | Source-of-truth markdown that humans and agents both read     | Always                                 |
| 🤖 **Claude skills**  | Reusable workflows the agent invokes on demand                | Always (if you use Claude Code)        |
| 🪝 **Claude hooks**   | Mechanical guardrails the harness enforces on every tool call | Always (if you use Claude Code)        |
| 💬 **Slash commands** | User-triggered prompts you invoke with `/<name>`              | Always (if you use Claude Code)        |
| 🐳 **Docker stacks**  | Opinionated `docker-compose` setups per tech stack            | When your project ships a backend / DB |
| 🪛 **Scripts**        | Standalone CLIs that operate on the project                   | As needed                              |

---

## 📋 The prompt shelf

The contract between you, your project, and any agent working on it. Keep these tight and current — they're loaded into every coding session.

1. **`SPEC.md`** — **The "What."** Product requirements, user stories, milestones.
2. **`ARCHITECTURE.md`** — **The "Where."** Tech stack, directory structure, system flow.
3. **`AGENTS.md`** — **The "How."** Engineering standards, anti-patterns, git workflow. The single source of truth for technical rules.
4. **`KNOWLEDGE.md`** — **The "Vocabulary."** Domain glossary and shared understandings. Keeps the codebase, docs, and conversation using the same words for the same things.
5. **`MEMORY.md`** — **The "Journal."** Agent-maintained record of quirks, bugs, and patterns. Prevents repeating past mistakes.
6. **`IMPLEMENTATION_PLAN.md`** — **The "When."** Living task tracker and inter-agent handoff doc. Created when execution starts.

Two thin per-agent files (`CLAUDE.md`, `GEMINI.md`) point each tool at `AGENTS.md` so the rules stay in one place.

## 🤖 The Claude skill bundle

`claude/skills/` ships seven Claude Code skills that get symlinked into your shell's `~/.claude/skills/` directory. Each is a self-contained workflow the agent invokes automatically when it matches your request.

| Skill                          | What it does                                                                                                                                                                                                          |
| ------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 🧑‍⚖️ **`agent-code-reviewer`**   | Get a second-opinion review from a different model (Gemini or Codex) via `cli/agent_code_reviewer.py`. Reviewer feedback only — never writes code.                                                                    |
| 🎓 **`deep-discuss`**          | The agent grills you on a plan or design until you've resolved every branch of the decision tree, stress-testing it against the project glossary (`KNOWLEDGE.md`) and recorded decisions (RFCs). Use before building. |
| 🤝 **`handoff`**               | Compact the current conversation into a handoff doc another agent (or future-you) can pick up.                                                                                                                        |
| 🌱 **`new-project-setup`**     | Walks fork-time decisions (project slug, ORM choice, ngrok, PG extensions, port collisions) and substitutes Docker placeholders in one batch.                                                                         |
| 🔄 **`project-template-sync`** | Back-ports lessons from a downstream project into this template. Generalizes project-specific rules into reusable foundation.                                                                                         |
| 🚀 **`pull-request-creator`**  | Fixed PR title format, body template, attribution conventions, and `pr-review-toolkit` follow-up.                                                                                                                     |
| 🔭 **`sentry-cli`**            | Inspect Sentry issues, events, projects, orgs from the command line.                                                                                                                                                  |

The global rules file (`claude/CLAUDE.md`) ships alongside the skills as a starter for your `~/.claude/CLAUDE.md`.

## 🪝 The Claude hook bundle

`hooks/` ships shell scripts the Claude Code harness invokes on lifecycle events — a matching tool call (`PreToolUse`) or the agent finishing a turn (`Stop`). Unlike skills (which the agent chooses to invoke), hooks are **mechanical guardrails** — the harness runs them regardless of what the agent wants, so they're the right fix for failure modes behavioral rules can't reliably prevent.

| Hook                                  | Event                                                  | What it does                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| ------------------------------------- | ------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 🚧 **`enforce-worktree-boundary.sh`** | `PreToolUse` on `Edit\|Write\|MultiEdit\|NotebookEdit` | Blocks any edit whose `file_path` resolves to a different git worktree than the session's cwd. Fixes the silent cross-worktree-edit trap: agent runs `rg` from a parent dir, gets absolute paths into the wrong checkout, then writes there because the edit tools don't validate against cwd. Allows edits inside the session's worktree, and allows edits outside any git repo (`~/.claude/`, `/tmp/`, etc.). Bypass with `--dangerously-skip-permissions` or by removing the hook from `~/.claude/settings.json`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| 📓 **`knowledge-reconcile.sh`**       | `Stop`                                                 | Nudges the agent to reconcile `KNOWLEDGE.md` when the branch introduces a new domain **type** (`type`/`interface`/`enum`/Prisma `model`/Zod schema) whose name isn't in any `KNOWLEDGE*.md`. Keys off the branch diff, not the conversation, so a UI/bugfix session that adds no new type stays silent — and the nudge says to make no edits and no summary if the types turn out to be plumbing. Fires at most once per session; skipped when no glossary exists, when a `KNOWLEDGE*.md` was already edited this session, or when the glossary still carries the `knowledge-reconcile:skip` marker (delete it once you seed real terms). Points the agent at `commands/update-knowledge.md` (the same procedure `/update-knowledge` runs) — no duplicated instructions. Type-extraction regexes assume TS/Prisma; tune for other stacks. Loop-safe via `stop_hook_active` + a once-per-session marker. Design rationale + tuning ledger: [`docs/experiments/knowledge-reconcile.md`](docs/experiments/knowledge-reconcile.md). |

Install by symlinking the directory into your Claude config, then registering each hook in `~/.claude/settings.json`:

```bash
ln -s ~/code/agentic_coding_project_template/hooks ~/.claude/hooks
```

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write|MultiEdit|NotebookEdit",
        "hooks": [
          { "type": "command", "command": "$HOME/.claude/hooks/enforce-worktree-boundary.sh" }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [{ "type": "command", "command": "$HOME/.claude/hooks/knowledge-reconcile.sh" }]
      }
    ]
  }
}
```

## 💬 The slash commands

`commands/` ships custom slash commands — markdown prompt files you invoke with `/<name>`. Unlike skills (which the agent auto-selects), these are user-triggered, and some double as the single source of truth that a hook points at.

| Command                    | What it does                                                                                                                                                                                                                                                                                   |
| -------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 📓 **`/update-knowledge`** | Reconciles `KNOWLEDGE.md` against the domain terms discussed this session — lists each term, marks it recorded/updated/missing, writes the gaps. Run it manually anytime; the `knowledge-reconcile.sh` Stop hook also points the agent at this same file, so the procedure lives in one place. |

Install by symlinking the directory (or per-command, to avoid clobbering your own):

```bash
ln -s ~/code/agentic_coding_project_template/commands ~/.claude/commands
```

## 🐳 The Docker stacks

`docker/` ships drop-in dev stacks. Each is a fork-and-customize starter, not a library.

- **`docker/nextjs/`** — Next.js + PostgreSQL 18 + pgvector + Prisma (default; Drizzle swap documented). Two-file compose split (long-lived infra + per-worktree app) sized for multi-agent worktree development.

Each stamp has its own README explaining placement, env vars, and profile activation. **Don't `cp -a` and edit by hand** — invoke the `new-project-setup` skill from your new project's directory.

## 🪛 The scripts

`cli/` holds standalone tools that operate on the project but live outside the app code.

| Script                       | Purpose                                                                                                                                                        |
| ---------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **`agent_code_reviewer.py`** | Multi-provider second-opinion reviewer (Gemini + Codex). Run `python3 cli/agent_code_reviewer.py --help` for flags, or invoke the `agent-code-reviewer` skill. |
| **`worktree-add.sh`**        | Create a new git worktree wired up for the Docker stack — auto-assigns ports, writes per-worktree `.env.docker`, prints bring-up commands.                     |

See `cli/README.md` for script-authoring conventions.

## ⚙️ The tooling stubs

- **`.gitignore`** — covers `.env.docker`, `.env*.local`, `node_modules/`, framework build output. Prevents first-commit credential leaks.
- **`.prettierrc`** + **`tsconfig.json`** — baseline configs that work out of the box for the Next.js stamp's `web/` directory.
- **`.github/workflows/ci.yml`** — minimal CI: `prettier --check`, `tsc --noEmit`, test suite stub.

---

## 🧭 How to use this template

1. **Copy the prompt shelf** (`SPEC.md`, `ARCHITECTURE.md`, `AGENTS.md`, `KNOWLEDGE.md`, `MEMORY.md`) and the per-agent pointer files (`CLAUDE.md`, `GEMINI.md`) to your new project root.
2. **Copy the tooling stubs** (`.gitignore`, `.prettierrc`, `tsconfig.json`, `.github/`, `cli/`).
3. **Symlink the individual skills you want** into your Claude config (`~/.claude/skills/` likely already has your own — symlink per-skill instead of globbing so you don't clobber anything):
   ```bash
   ln -s ~/code/agentic_coding_project_template/claude/skills/handoff ~/.claude/skills/handoff
   ln -s ~/code/agentic_coding_project_template/claude/skills/new-project-setup ~/.claude/skills/new-project-setup
   # ...repeat for any others you find useful
   ```
4. **Edit `SPEC.md`** first — define the problem and requirements.
5. **Refine `ARCHITECTURE.md`** — lock in tech stack and folder structure.
6. **Update `AGENTS.md`** with project-specific standards and "Hard Refusal" anti-patterns.
7. **Seed `KNOWLEDGE.md`** with the domain terms your project relies on — or let a `deep-discuss` session populate it as decisions firm up. Delete the `knowledge-reconcile:skip` marker at the top once you've added real terms, so the `knowledge-reconcile.sh` Stop hook starts keeping the glossary current.
8. **Initialize `MEMORY.md`** (or let the agent do it) to start capturing project context.
9. **For Docker:** copy the relevant `docker/<stamp>/` contents to the project root and invoke the `new-project-setup` skill — do not edit Docker files by hand.

## 💭 The philosophy

**Documentation is code.** If an agent or a new developer cannot understand the project's intent and constraints by reading these files, the project is under-documented.

- **`AGENTS.md`** ensures the rules of engagement are explicit.
- **`KNOWLEDGE.md`** ensures everyone uses the same words for the same things.
- **`MEMORY.md`** ensures hard-earned context isn't lost between sessions.
- **`IMPLEMENTATION_PLAN.md`** ensures complex tasks are broken down and dependencies are respected.
- **The skill bundle** ensures repeatable workflows don't drift from session to session.

Use the "Good/Bad" examples within the template as a guide for your own documentation.
