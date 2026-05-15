---
name: new-project-setup
description: Use when bootstrapping a new project from the agentic_coding_project_template (especially its docker/ stack), OR when modifying docker/ services in an existing project (adding ngrok, switching ORM, adding a PG extension, renaming the shared network). Walks the user through fork-time decisions BEFORE editing files.
---

# New-Project Setup Walkthrough

## Overview

The template's `docker/` stamps ship with opinionated defaults: PostgreSQL 18 + pgvector + Prisma + named volumes + the infra/app worktree split. These defaults are the user's standard stack, but every fork has at least a few decisions that diverge — and "blindly accept the defaults" is wrong often enough that it must be asked, not assumed.

This skill captures the fork-time questions and the exact substitutions each answer triggers. Ask every question below before writing to any file in `docker/`.

**Violating the spirit of these questions wastes the user's time.** Defaults are right ~80% of the time and silently wrong ~20%. Always ask.

## Red Flags — STOP

| Rationalization                                           | Reality                                                                                                                                                 |
| --------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| "The Dockerfile already has Prisma, I'll just keep it"    | Prisma is the _template_ default, not necessarily the _project's_ choice. Ask.                                                                          |
| "I'll substitute `app_shared` for the project name later" | Forgetting leaves two projects on the same machine colliding on one network. Do it before first `up`.                                                   |
| "ngrok isn't running so I don't need to ask"              | If the project needs public dev preview (OAuth callbacks, webhook testing), configure it now — not after the user hits a wall.                          |
| "I'll skip pgvector if it's not used yet"                 | pgvector is one apt line. Adding it later means `down -v`, image rebuild, volume loss. Ask up front.                                                    |
| "The user said 'just set up Docker'"                      | "Set up Docker" still means "ask the substitution questions." A user-friendly skill that asks two questions beats a one-shot that ships wrong defaults. |

## Workflow

Ask the questions below in order. After all answers are in, perform the substitutions in one batch and surface the diff via `git diff` before any commit.

### Q1: Project slug (BLOCKING)

Ask: _"What's the project slug? It namespaces the shared Docker network and per-worktree containers — needed to avoid collisions with other projects on this machine. Lowercase, hyphen- or underscore-separated. Example: `taskbird`, `analytics_pipeline`."_

Substitutions:

- `docker-compose.infra.yml` — `app_shared` → `<slug>_shared` (network name _and_ the `name:` field)
- `docker-compose.app.yml` — `app_shared` → `<slug>_shared` (network name _and_ the `name:` field)
- `.env.docker.example` — update the `COMPOSE_PROJECT_NAME` default from `app-main` to `<slug>-main`, and `WORKTREE_DB` from `app_dev_main` to `<slug>_dev_main`
- `docker-compose.infra.yml` — `POSTGRES_DB` from `app_dev` to `<slug>_dev` (the catalog database, not the worktree one)

### Q2: ORM choice (BLOCKING)

Ask: _"Which ORM? Default is Prisma. Other options: Drizzle, Kysely, no ORM."_

**Prisma** → no changes. Default is correct.

**Drizzle** → the README's "Swapping ORMs → Drizzle" section has the exact replacement blocks. Apply all four:

- `docker-compose.app.yml`: replace the fenced `studio:` block with the Drizzle variant (different port: 4983 internal, different command: `npx drizzle-kit studio`).
- `web/Dockerfile.dev`: replace the three fenced blocks with the Drizzle no-op variants (no `COPY prisma/`, no `prisma generate`, CMD becomes `npx drizzle-kit migrate && npm run dev`).

**Kysely / no ORM** → strip Prisma fences entirely:

- Delete the `studio:` service from `docker-compose.app.yml` (or replace with project-specific tooling).
- In `web/Dockerfile.dev`, remove Prisma `COPY`, remove `prisma generate`, and replace the final `CMD` with `CMD ["npm", "run", "dev"]`.
- Ask the user where migrations get applied (out-of-band CLI? init container? skip for now?).

### Q3: ngrok (NON-BLOCKING)

Ask: _"Does this project need a public ngrok tunnel for the dev server? Common reasons: OAuth callbacks requiring HTTPS, webhook testing from third parties, sharing previews with non-devs."_

**Yes** → ask for the reserved ngrok domain. ngrok's free tier supports one static domain per account, so document which worktree (which `WEB_PORT`) wins the tunnel.

- `docker-compose.infra.yml`: `YOUR_NGROK_DOMAIN` → the domain.
- `.env.docker.example`: uncomment `COMPOSE_PROFILES` and include `ngrok`; uncomment `NGROK_AUTHTOKEN=` placeholder.

**No** → leave the service in place (profile-gated, won't run). The user can flip it on later with one env-var change, no merge.

### Q4: Extra Postgres extensions (NON-BLOCKING)

Ask: _"pgvector is included by default. Need any other PG extensions now? Common ones: PostGIS (geospatial), pg_partman (time-series partitioning), TimescaleDB, pg_uuidv7 (only if you want DB-side UUIDv7 on PG14-17 — PG18's native `uuidv7()` covers most cases)."_

**Yes** → add an apt line per extension to `Dockerfile.db`. Each extension also needs a `CREATE EXTENSION` statement in a migration to activate inside a given database.

**No / unsure** → skip; the user can add extensions later (with a rebuild cost — call this out).

### Q5: Memory limits (NON-BLOCKING — ask only on signal)

Defaults: web 6g, db 1g, studio 500m, ngrok 500m. 6g on web is sized for Next.js + TypeScript + Prisma during dev/build. Ask only if the user has signaled a constraint (low-memory machine, many parallel worktrees). Don't volunteer this question for a typical setup.

If lowering: substitute the `memory:` line in `docker-compose.app.yml` (web) — 2-3g is reasonable for API-only or lighter SSR work.

## After substitution

1. Run `git diff` and show the user every change you made.
2. Prompt: _"Run `cp .env.docker.example .env.docker` and edit per-worktree values (`WEB_PORT`, `STUDIO_PORT`, `WORKTREE_DB`, `COMPOSE_PROJECT_NAME`) before bringing the stack up."_
3. Recommend the bring-up order: `docker compose -f docker-compose.infra.yml up -d` once per machine, then `docker compose -f docker-compose.app.yml --env-file .env.docker up` per worktree.
4. Do **not** run `docker compose up` yourself unless the user explicitly asks. Long-running processes and "is this healthy?" judgement belong to the user on first boot.

## Common mistakes

| Mistake                                                 | Fix                                                                                                                                     |
| ------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| Substituted `app_shared` in only one file               | The two compose files must agree exactly — name mismatch means the app stack can't join the infra network.                              |
| Replaced only some ORM fences                           | An app.yml `studio:` running Prisma against a Drizzle codebase fails on `up`. Replace _all_ fences in _both_ files.                     |
| Skipped Q4 and added an extension later                 | `down -v` + image rebuild = volume loss. Bring this up at bootstrap.                                                                    |
| Forgot ngrok target port                                | ngrok's `host.docker.internal:3000` only forwards to the worktree publishing `WEB_PORT=3000`. Document which worktree that is.          |
| Edited `.env.docker.example` instead of `.env.docker`   | `.example` is the source of truth for which vars _exist_; the real one is per-worktree, gitignored, and is what Compose actually reads. |
| Ran `docker compose restart` to pick up env-var changes | `restart` does not re-read env files. Use `up -d` (with `--build -V` if dependencies changed).                                          |
