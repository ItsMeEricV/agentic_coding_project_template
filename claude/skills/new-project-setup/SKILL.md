---
name: new-project-setup
description: Use when bootstrapping a new project from the agentic_coding_project_template (especially its docker/ stack), OR when modifying docker/ services in an existing project (adding ngrok, switching ORM, adding a PG extension, renaming the shared network). Walks the user through fork-time decisions BEFORE editing files.
---

# New-Project Setup Walkthrough

## Overview

The template's `docker/` stamps ship with opinionated defaults: PostgreSQL 18 + pgvector + Prisma + named volumes + the infra/app worktree split. These defaults are the user's standard stack, but every fork has at least a few decisions that diverge — and "blindly accept the defaults" is wrong often enough that it must be asked, not assumed.

This skill captures the fork-time questions and the exact substitutions each answer triggers. Ask every question below before writing to any file in `docker/`.

It also covers two environment concerns that aren't in `docker/` but belong at bootstrap: how many deploy environments the project has (Q6), and how environment variables are declared and detected via a single `environment.ts` (Q7). Both default sensibly but are silently wrong often enough to ask.

**Violating the spirit of these questions wastes the user's time.** Defaults are right ~80% of the time and silently wrong ~20%. Always ask.

## Red Flags — STOP

| Rationalization                                           | Reality                                                                                                                                                 |
| --------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| "The Dockerfile already has Prisma, I'll just keep it"    | Prisma is the _template_ default, not necessarily the _project's_ choice. Ask.                                                                          |
| "I'll substitute `app_shared` for the project name later" | Forgetting leaves two projects on the same machine colliding on one network. Do it before first `up`.                                                   |
| "ngrok isn't running so I don't need to ask"              | If the project needs public dev preview (OAuth callbacks, webhook testing), configure it now — not after the user hits a wall.                          |
| "I'll skip pgvector if it's not used yet"                 | pgvector is one apt line. Adding it later means `down -v`, image rebuild, volume loss. Ask up front.                                                    |
| "The user said 'just set up Docker'"                      | "Set up Docker" still means "ask the substitution questions." A user-friendly skill that asks two questions beats a one-shot that ships wrong defaults. |
| "I'll just add the env var I need to `process.env`"       | Every env var goes in the `environment.ts` Zod schema AND gets surfaced to the user. Silent `process.env.FOO` reads are the exact problem Q7 prevents.   |
| "I'll just collapse this to dev + prod, simpler"          | Number of environments is the user's call (Q6). Default is dev + preview + prod (preview → preview) to match Vercel's lanes; only drop the preview lane if they ask. |

## Workflow

Ask the questions below in order. After all answers are in, perform the substitutions in one batch and surface the diff via `git diff` before any commit.

### Q0: Web app prerequisite (BLOCKING)

The Docker stamp's `web/Dockerfile.dev` builds from `./web` and expects a `package.json` (and, for the Prisma default, `prisma/schema.prisma` + `prisma.config.ts`). On a brand-new fork these don't exist yet — the first `docker compose up web` will fail at the `COPY package*.json ./` step.

Check whether `web/package.json` exists. If yes, skip to Q1. If no, ask: _"There's no Next.js app in `web/` yet. Run `npx create-next-app@latest web` first? I'll walk through the prompts."_

Do not pin the Next.js version or force any specific create-next-app prompts — let the user pick TypeScript, ESLint, Tailwind, App Router, etc. Once `web/package.json` exists, return to this skill for Q1.

ORM-specific init runs **after** Q2 (so the install reflects the ORM the user actually chooses):

- Prisma → `cd web && npm install prisma @prisma/client && npx prisma init`
- Drizzle → `cd web && npm install drizzle-orm pg && npm install -D drizzle-kit @types/pg`
- Kysely / other → install per the user's preference; ask where migrations live
- No ORM → skip the install entirely

### Q1: Project slug + host-port collision (BLOCKING)

Ask: _"What's the project slug? It namespaces the shared Docker network, the db container name, and per-worktree containers — needed to avoid collisions with other projects on this machine. Lowercase, hyphen- or underscore-separated. Example: `taskbird`, `analytics_pipeline`."_

Then ask: _"Will any other project on this machine also publish Postgres on host port 5432? If yes, pick an alternate host port for this project's db (e.g. 5433, 5434). Default is 5432."_

Substitutions:

- `docker-compose.infra.yml` — `app_shared` → `<slug>_shared` (network name _and_ the `name:` field)
- `docker-compose.infra.yml` — `container_name: app_db` → `container_name: <slug>_db` (the network alias `db` stays unchanged, so the app stack's `DATABASE_URL` keeps using `db:5432` regardless)
- `docker-compose.infra.yml` — volume `app_postgres_data` → `<slug>_postgres_data` (top-level `volumes:` block _and_ the db service's mount)
- `docker-compose.infra.yml` — host port in `"5432:5432"` → `"<host-port>:5432"` (only the left side; the container always listens on 5432 internally)
- `docker-compose.infra.yml` — `POSTGRES_DB` from `app_dev` → `<slug>_dev` (the catalog database, not the worktree one)
- `docker-compose.app.yml` — `app_shared` → `<slug>_shared` (network name _and_ the `name:` field)
- `.env.docker.example` — `COMPOSE_PROJECT_NAME` default from `app-main` → `<slug>-main`, `WORKTREE_DB` from `app_dev_main` → `<slug>_dev_main`

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

**Yes** → two more questions:

1. _"What's your reserved ngrok domain?"_ (free tier supports one static domain per account)
2. _"Which worktree's `WEB_PORT` wins the public URL?"_ Default 3000 (the "main" worktree). Only one worktree at a time can be tunneled because the ngrok command targets a single host port.

Substitutions:

- `docker-compose.infra.yml` (ngrok `command`) — `YOUR_NGROK_DOMAIN` → the domain.
- `docker-compose.infra.yml` (ngrok `command`) — `host.docker.internal:3000` → `host.docker.internal:<chosen-port>` if the user picked a non-3000 port.
- `.env.docker.example` — uncomment `COMPOSE_PROFILES` and include `ngrok`; uncomment `NGROK_AUTHTOKEN=` placeholder.

**No** → leave the service in place (profile-gated, won't run). The user can flip it on later with one env-var change, no merge.

### Q4: Extra Postgres extensions (NON-BLOCKING)

Ask: _"pgvector is included by default. Need any other PG extensions now? Common ones: PostGIS (geospatial), pg_partman (time-series partitioning), TimescaleDB, pg_uuidv7 (only if you want DB-side UUIDv7 on PG14-17 — PG18's native `uuidv7()` covers most cases)."_

**Yes** → add an apt line per extension to `Dockerfile.db`. Each extension also needs a `CREATE EXTENSION` statement in a migration to activate inside a given database.

**No / unsure** → skip; the user can add extensions later (with a rebuild cost — call this out).

### Q5: Memory limits (NON-BLOCKING — ask only on signal)

Defaults: web 6g, db 1g, studio 500m, ngrok 500m. 6g on web is sized for Next.js + TypeScript + Prisma during dev/build. Ask only if the user has signaled a constraint (low-memory machine, many parallel worktrees). Don't volunteer this question for a typical setup.

If lowering: substitute the `memory:` line in `docker-compose.app.yml` (web) — 2-3g is reasonable for API-only or lighter SSR work.

### Q6: Environment split (BLOCKING)

Ask: _"How many deploy environments does this project need? Default is **development + preview + production**, which maps cleanly onto Vercel's three lanes (local / preview / production). Options: that default three, just development + production, or a single environment (local only / one deploy lane). This decides the `AppEnv` enum and the Vercel-lane detection in `environment.ts` (Q7)."_

The default lane is named `preview` to match Vercel's own `VERCEL_ENV=preview` value, so detection is near-identity. If the user prefers the word "staging," rename `'preview' → 'staging'` in the file — the underlying Vercel value is always `preview`.

Map the answer onto the `references/environment.ts` template:

- **dev + preview + prod** (default) — use the reference as-is. `'preview' → 'preview'` mirrors Vercel's preview lane, so there's nothing to trim.
- **development + production** — delete the `'preview'` entry from `APP_ENVS`, drop `isPreview`, and in `detectEnvironment()` map `'preview' → 'production'` (preview deploys exercise prod-like paths). The trim notes in the reference call out each line to change.
- **single environment** — keep only `'production'` in `APP_ENVS`; `detectEnvironment()` can `return 'production'`. Drop the `is*` flags the project won't branch on.

If the user is unsure, take the default (dev + preview + prod) and say so — it matches Vercel's lanes out of the box, and collapsing to dev + prod later is a small edit to this one file.

### Q7: Environment variables + `environment.ts` (BLOCKING)

The template's biggest silent-footgun is unmanaged environment variables — vars created ad hoc, scattered across `process.env.FOO` reads, with no inventory and no record of which lane each belongs to. Prevent this at bootstrap by installing one `environment.ts` as the single source of truth.

Copy `references/environment.ts` to `web/src/environment.ts`, then trim it per the Q6 answer. The file gives the project:

- the `AppEnv` enum + `ENVIRONMENT` label and `isDevelopment` / `isPreview` / `isProduction` guards,
- Vercel deploy-lane detection via `NEXT_PUBLIC_VERCEL_ENV` (works server-side and in the browser bundle), with a strict-mode throw on unrecognized values so a misconfigured deploy fails loud instead of silently running as `development`,
- vitest / test-runner detection (`isTesting`, `isVitestRunning`),
- one Zod `EnvSchema` that is the **only** place `process.env` is read.

State the rule to the user and follow it for the rest of setup: **every environment variable goes through `EnvSchema` in `environment.ts`, gets a matching entry in `.env.docker.example`, and is announced to the user when added — never introduced silently.** If the project isn't Next.js + Vercel, the detection signal (`NEXT_PUBLIC_VERCEL_ENV`) must be swapped for that platform's equivalent — flag this rather than shipping the file unchanged.

(The reference intentionally omits Edge Config and other specialized vars — add those per-project, through the same schema.)

## After substitution

1. Run `git diff` and show the user every change you made.
2. If `web/src/` exists, write `web/src/environment.ts` from `references/environment.ts`, trimmed per the Q6 split, and run `npx prettier --write web/src/environment.ts`. Show it in the diff alongside the docker changes.
3. Prompt: _"Run `cp .env.docker.example .env.docker` and edit per-worktree values (`WEB_PORT`, `STUDIO_PORT`, `WORKTREE_DB`, `COMPOSE_PROJECT_NAME`) before bringing the stack up."_
4. Recommend the bring-up order:
   - Once per machine: `docker compose -f docker-compose.infra.yml --env-file .env.docker up -d` (the `--env-file` is required so `COMPOSE_PROFILES` and `NGROK_AUTHTOKEN` are read; the per-worktree vars are harmlessly ignored by infra services).
   - Once per worktree: `docker compose -f docker-compose.app.yml --env-file .env.docker up`.
   - On first `up` of the app stack, the `db-init` service creates the worktree database inside the shared Postgres and exits; `web` and `studio` are gated on its successful completion.
5. Do **not** run `docker compose up` yourself unless the user explicitly asks. Long-running processes and "is this healthy?" judgement belong to the user on first boot.

## Common mistakes

| Mistake                                                         | Fix                                                                                                                                                                                                                     |
| --------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Substituted `app_shared` in only one file                       | The two compose files must agree exactly — name mismatch means the app stack can't join the infra network.                                                                                                              |
| Substituted network but forgot `container_name` / port / volume | Two projects on the same machine collide on `container_name: app_db`, host port 5432, or the `app_postgres_data` volume. The network alias `db` stays stable; only the container name, host port, and volume name move. |
| Replaced only some ORM fences                                   | An app.yml `studio:` running Prisma against a Drizzle codebase fails on `up`. Replace _all_ fences in _both_ files.                                                                                                     |
| Skipped Q4 and added an extension later                         | `down -v` + image rebuild = volume loss. Bring this up at bootstrap.                                                                                                                                                    |
| Forgot ngrok target port                                        | ngrok's `host.docker.internal:3000` only forwards to the worktree publishing `WEB_PORT=3000`. Document which worktree that is.                                                                                          |
| Edited `.env.docker.example` instead of `.env.docker`           | `.example` is the source of truth for which vars _exist_; the real one is per-worktree, gitignored, and is what Compose actually reads.                                                                                 |
| Ran infra `up` without `--env-file .env.docker`                 | `COMPOSE_PROFILES=ngrok` in `.env.docker` is silently ignored without the flag, so ngrok stays disabled even when the user thought they enabled it.                                                                     |
| Ran `docker compose restart` to pick up env-var changes         | `restart` does not re-read env files. Use `up -d` (with `--build -V` if dependencies changed).                                                                                                                          |
| Collapsed to dev + prod without asking                          | Environment count is the user's call (Q6). Default is dev + preview + prod (`preview → preview`, matching Vercel); only drop the preview lane when the user asks.                                                         |
| Added `process.env.FOO` read without touching `environment.ts`  | Every var goes through `EnvSchema` in `environment.ts` + `.env.docker.example`, and is announced to the user. Scattered silent `process.env` reads are exactly what Q7 exists to stop.                                   |
| Shipped `environment.ts` unchanged on a non-Vercel project      | The `NEXT_PUBLIC_VERCEL_ENV` detection only works on Vercel. Swap the signal for the target platform's equivalent, or detection silently resolves to `development` everywhere.                                            |
