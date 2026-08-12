# Agentic Coding Project Template 🛠️

> **What is this?** A drop-in foundation for AI-assisted coding projects. It bundles the markdown files agents read to understand your project, a set of Claude Code skills that automate common workflows, opinionated Docker dev stacks, and a few small scripts. Fork the relevant pieces into a new project, fill in the placeholders, and your coding agents arrive pre-briefed.

The repo has seven halves, each independently useful:

| Pillar                | What it is                                                    | When you want it                       |
| --------------------- | ------------------------------------------------------------- | -------------------------------------- |
| 📋 **Prompt shelf**   | Source-of-truth markdown that humans and agents both read     | Always                                 |
| 🌐 **Global rules**   | Your cross-project rules, symlinked into each agent's config  | Always                                 |
| 🤖 **Claude skills**  | Reusable workflows the agent invokes on demand                | Always (if you use Claude Code)        |
| 🪝 **Agent hooks**    | Mechanical guardrails the harness enforces on every tool call | Always (Claude Code, and `pi` via an adapter) |
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

Two thin per-agent files (`CLAUDE.md`, `GEMINI.md`) point each tool at `AGENTS.md` so the rules stay in one place. `CLAUDE.md` opens with an `@AGENTS.md` import, because Claude Code reads `CLAUDE.md` and **not** `AGENTS.md` — without the import the rules never reach the context window. `pi` and Codex read `AGENTS.md` natively and need no pointer.

## 🤖 The Claude skill bundle

`claude/skills/` ships six Claude Code skills that get symlinked into your shell's `~/.claude/skills/` directory. Each is a self-contained workflow the agent invokes automatically when it matches your request.

| Skill                          | What it does                                                                                                                                                                                                          |
| ------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 🧑‍⚖️ **`agent-code-reviewer`**   | Get a second-opinion review from a different model (Gemini or Codex) via `cli/agent_code_reviewer.py`. Reviewer feedback only — never writes code.                                                                    |
| 🎓 **`deep-discuss`**          | The agent grills you on a plan or design until you've resolved every branch of the decision tree, stress-testing it against the project glossary (`KNOWLEDGE.md`) and recorded decisions (RFCs). Use before building. |
| 🤝 **`handoff`**               | Compact the current conversation into a handoff doc another agent (or future-you) can pick up.                                                                                                                        |
| 🌱 **`new-project-setup`**     | Walks fork-time decisions (project slug, ORM choice, ngrok, PG extensions, port collisions) and substitutes Docker placeholders in one batch.                                                                         |
| 🔄 **`project-template-sync`** | Back-ports lessons from a downstream project into this template. Generalizes project-specific rules into reusable foundation.                                                                                         |
| 🚀 **`pull-request-creator`**  | Fixed PR title format, body template, attribution conventions, and `pr-review-toolkit` follow-up.                                                                                                                     |

`pi` loads these same skills — point its `settings.json` at the directory with `"skills": ["~/.claude/skills"]`.

## 🌐 Global agent rules

There are **two kinds of `AGENTS.md`** in this repo, and the difference is scope:

| | Lives at | Scope | Copied per project? |
| --- | --- | --- | --- |
| **Global** | `global/AGENTS.md` | Rules that follow *you* into every repo you open, on this machine | **No** — one file, symlinked |
| **Per-project** | `AGENTS.md` (repo root) | Engineering standards for *one* codebase | **Yes** — copied and customized per project |

They stay separate because they have opposite lifetimes. The per-project file is *meant* to fork — a downstream project's copy grows its own stack-specific rules. The global file must *never* fork, or changing your communication style means editing it in every project you own.

`global/` holds the files that symlink into your agents' config directories. Anything harness-specific sits in a subdirectory mirroring that agent's config path, so `global/pi/agent/` lands at `~/.pi/agent/`:

```
global/
├── AGENTS.md                             -> ~/.claude/CLAUDE.md  AND  ~/.pi/agent/AGENTS.md
└── pi/agent/
    ├── APPEND_SYSTEM.md                  -> ~/.pi/agent/APPEND_SYSTEM.md
    └── extensions/pretooluse-hooks.ts   -> ~/.pi/agent/extensions/pretooluse-hooks.ts
```

| File                             | Holds                                                                            |
| -------------------------------- | -------------------------------------------------------------------------------- |
| `global/AGENTS.md`               | Harness-agnostic rules: communication style, branch + commit workflow, PR conventions, anti-patterns |
| `global/pi/agent/APPEND_SYSTEM.md` | `pi`-only: which CLI to use per external service (`gh`, `neonctl`, `vercel`, `stripe`, `axiom`, `sentry`, `playwright cli`, Context7 over HTTP) |
| `global/pi/agent/extensions/pretooluse-hooks.ts` | `pi`-only: runs the `hooks/` `PreToolUse` scripts on `pi` tool calls — see [Hooks](#-hooks) |

```bash
ln -s ~/code/agentic_coding_project_template/global/AGENTS.md ~/.claude/CLAUDE.md
ln -s ~/code/agentic_coding_project_template/global/AGENTS.md ~/.pi/agent/AGENTS.md
ln -s ~/code/agentic_coding_project_template/global/pi/agent/APPEND_SYSTEM.md ~/.pi/agent/APPEND_SYSTEM.md
```

**Why `pi` gets two rules files and Claude gets one.** The agents differ in exactly one way: Claude has MCP servers, `pi` does not — so `pi` needs CLI instructions that would be wrong for Claude. `pi` loads two global files from `~/.pi/agent/`: `AGENTS.md` (context file) and `APPEND_SYSTEM.md` (appended to the system prompt). That second slot is what makes the split possible — `pi` gets the shared rules through one symlink and its CLI tooling through the other, so neither file needs a copy of the other's content. Claude reads only `~/.claude/CLAUDE.md`, so it sees the shared rules and never the CLI mappings.

Every rule lives in exactly one file. Edit `global/AGENTS.md` and both agents pick it up; edit `global/APPEND_SYSTEM.md` and only `pi` does.

## 🪝 Hooks

`hooks/` ships shell scripts the Claude Code harness invokes on lifecycle events — a matching tool call (`PreToolUse`) or the agent finishing a turn (`Stop`). Unlike skills (which the agent chooses to invoke), hooks are **mechanical guardrails** — the harness runs them regardless of what the agent wants, so they're the right fix for failure modes behavioral rules can't reliably prevent.

| Hook                                  | Event                                                  | What it does                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| ------------------------------------- | ------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 🚧 **`enforce-worktree-boundary{,-bash}.sh`** | `PreToolUse` on `Edit\|Write\|MultiEdit\|NotebookEdit` + `Bash` | Blocks work that escapes the session's worktree. The edit-tool hook blocks any edit whose `file_path` resolves to a different git worktree (agent `rg`s from a parent dir, gets absolute paths into the wrong checkout, writes there); the `-bash` companion blocks a command that `cd`/`pushd`es into a different worktree (`cd /path/to/main && npx prettier --write web/…`, which would format the main checkout, not the worktree edits). Detects the escape, not a per-tool allowlist — nothing rots. Allows in-tree work and anything outside a repo (`~/.claude/`, `/tmp/`). Not caught: a bare absolute path with no `cd`. Bypass by unregistering the hook (Claude: `~/.claude/settings.json`; `pi`: `~/.pi/agent/extensions/`).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
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
      },
      {
        "matcher": "Bash",
        "hooks": [
          { "type": "command", "command": "$HOME/.claude/hooks/enforce-worktree-boundary-bash.sh" }
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

### Same hooks, under `pi`

`pi` has no hooks config — it has a TypeScript extension API — so `global/pi/agent/extensions/pretooluse-hooks.ts` adapts rather than reimplements. It catches `pi`'s `tool_call` event for `write`, `edit`, and `bash`, hands the matching script the same Claude-shaped JSON on stdin, and turns exit 2 back into `pi`'s `{ block: true }`. The rule keeps one implementation; only the adapter differs, so a fix to a script lands in both agents at once.

```bash
ln -s ~/code/agentic_coding_project_template/global/pi/agent/extensions/pretooluse-hooks.ts ~/.pi/agent/extensions/pretooluse-hooks.ts
```

It resolves the scripts through `~/.claude/hooks/` — the symlink above — which is the same cross-harness borrowing `pi` already does for skills via `"skills": ["~/.claude/skills"]` in `~/.pi/agent/settings.json`. If a script is missing, the extension stays out of the way. Only `PreToolUse` is adapted; `knowledge-reconcile.sh` (a `Stop` hook) runs under Claude alone.

### Adding a hook

1. **Write the script** into `hooks/`. It reads the event JSON on stdin; for `PreToolUse`, exit 2 with an explanation on stderr to block, exit 0 to allow. Nothing to install — `~/.claude/hooks` already symlinks to this directory.
2. **Register it** in `~/.claude/settings.json` under its event, matching the JSON above.
3. **Add a row** to the hook table so the next reader knows it exists.
4. **For `pi`** (`PreToolUse` only): add the filename to `GUARDS` in `global/pi/agent/extensions/pretooluse-hooks.ts`, under each `pi` tool it should guard. Note the tool names differ from Claude's matchers — `pi` has `edit`, `write`, and `bash`, and its `edit` covers what Claude splits across `Edit`/`MultiEdit`. Scripts listed for a tool run in order until one blocks.

Test a `PreToolUse` script by piping it a payload directly — `echo '{"cwd":"'$PWD'","tool_input":{"command":"ls"}}' | hooks/your-hook.sh; echo $?` — which is exactly what both harnesses do to it.

The published [`@hsingjui/pi-hooks`](https://github.com/hsingjui/pi-hooks) package does the general version of this — the whole Claude hooks schema, every event. It's the right call if you want all your hooks ported; this repo keeps the ~80-line adapter instead because a package that intercepts every tool call runs with full system permissions, and two guards don't need a dependency for that.

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
4. **Symlink the global rules** into each agent's config — see [Global agent rules](#-global-agent-rules) for the three commands.
5. **Edit `SPEC.md`** first — define the problem and requirements.
6. **Refine `ARCHITECTURE.md`** — lock in tech stack and folder structure.
7. **Update `AGENTS.md`** with project-specific standards and "Hard Refusal" anti-patterns.
8. **Seed `KNOWLEDGE.md`** with the domain terms your project relies on — or let a `deep-discuss` session populate it as decisions firm up. Delete the `knowledge-reconcile:skip` marker at the top once you've added real terms, so the `knowledge-reconcile.sh` Stop hook starts keeping the glossary current.
9. **Initialize `MEMORY.md`** (or let the agent do it) to start capturing project context.
10. **For Docker:** copy the relevant `docker/<stamp>/` contents to the project root and invoke the `new-project-setup` skill — do not edit Docker files by hand.

## 💭 The philosophy

**Documentation is code.** If an agent or a new developer cannot understand the project's intent and constraints by reading these files, the project is under-documented.

- **`AGENTS.md`** ensures the rules of engagement are explicit.
- **`KNOWLEDGE.md`** ensures everyone uses the same words for the same things.
- **`MEMORY.md`** ensures hard-earned context isn't lost between sessions.
- **`IMPLEMENTATION_PLAN.md`** ensures complex tasks are broken down and dependencies are respected.
- **The skill bundle** ensures repeatable workflows don't drift from session to session.

Use the "Good/Bad" examples within the template as a guide for your own documentation.
