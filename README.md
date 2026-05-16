# Agentic Coding Project Template

Foundation files for a new AI-assisted coding project. Two halves: **prompt-shelf markdown** (the "Source of Truth" for both human developers and AI agents) and **drop-in Docker dev stacks** for common tech stacks.

## The prompt shelf

1. **`SPEC.md`** — **The "What."** Product requirements, user stories, and milestones.
2. **`ARCHITECTURE.md`** — **The "Where."** Tech stack, directory structure, and system flow.
3. **`AGENTS.md`** — **The "How."** Engineering standards, anti-patterns, and git workflow.
4. **`MEMORY.md`** — **The "Journal."** An AI-maintained record of quirks, bugs, and patterns. Prevents repeating past mistakes and captures non-obvious context.
5. **`IMPLEMENTATION_PLAN.md`** — **The "When."** A living document for task tracking and inter-agent handovers. Created when execution starts.

## The Docker stacks

`docker/` ships opinionated drop-in development stacks for common project shapes:

- **`docker/nextjs/`** — Next.js + PostgreSQL 18 + pgvector + Prisma (default; Drizzle swap documented). Two-file compose split (long-lived infra + per-worktree app) sized for multi-agent worktree development.

Each stamp has its own README explaining placement, env vars, and profile activation. **Don't `cp -a` and edit by hand** — invoke the `new-project-setup` skill from your new project's directory. The skill walks through fork-time decisions (project slug, ORM choice, ngrok, PG extensions, host-port collisions) and substitutes placeholders in one batch.

## The tooling stubs

- **`.gitignore`** — covers `.env.docker`, `.env*.local`, `node_modules/`, framework build output. Prevents first-commit credential leaks.
- **`.prettierrc`** + **`tsconfig.json`** — baseline configs that work out of the box for the Next.js stamp's `web/` directory.
- **`.github/workflows/ci.yml`** — minimal CI: `prettier --check`, `tsc --noEmit`, test suite stub. Wire your project's test runner in once you have one.
- **`cli/worktree-add.sh`** — helper for the worktree pattern: creates a new git worktree, picks unused ports, writes a per-worktree `.env.docker`, prints the bring-up commands.

## How to use this Template

1. **Copy** the prompt-shelf files (`SPEC.md`, `ARCHITECTURE.md`, `AGENTS.md`, `MEMORY.md`) and the tooling stubs (`.gitignore`, `.prettierrc`, `tsconfig.json`, `.github/`, `cli/`) to the root of your new project.
2. **Edit `SPEC.md`** first to define the problem and requirements.
3. **Refine `ARCHITECTURE.md`** to lock in your tech stack and folder structure.
4. **Update `AGENTS.md`** with any project-specific standards and "Hard Refusal" anti-patterns.
5. **Initialize `MEMORY.md`** (or let the AI do it) to start capturing project context.
6. **Create `IMPLEMENTATION_PLAN.md`** (or let the AI do it) as you begin the execution phase.
7. **For Docker:** copy the relevant `docker/<stamp>/` contents to the project root and invoke the `new-project-setup` skill — do not edit Docker files by hand.

## The Philosophy

Documentation is code. If an agent or a new developer cannot understand the project's intent and constraints by reading these files, the project is under-documented.

- **`AGENTS.md`** ensures the rules of engagement are explicit.
- **`MEMORY.md`** ensures that "hard-earned" context isn't lost between sessions.
- **`IMPLEMENTATION_PLAN.md`** ensures that complex tasks are broken down and dependencies are respected.

Use the "Good/Bad" examples within the template as a guide for your own documentation.
