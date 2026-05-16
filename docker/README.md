# Docker Stamps

Drop-in Docker development stacks for new projects forked from this template. Each stamp is a complete, opinionated bundle — copy a stamp's contents to the root of your new project and you're ready to run.

## Currently shipped

| Stamp     | Stack                                                 | Purpose                                             |
| --------- | ----------------------------------------------------- | --------------------------------------------------- |
| `nextjs/` | Next.js + PostgreSQL 18 + pgvector + Prisma (default) | Web app dev stack with multi-agent worktree support |

## The infra/app split

Each stamp uses **two compose files**, not one. This split is load-bearing for the multi-agent worktree pattern that this template assumes:

- **`docker-compose.infra.yml`** — long-lived, shared across worktrees. Brought up **once per machine**. Owns the shared Docker network, the database container, and anything else that should be a singleton (ngrok tunnel, mail catcher, etc.).
- **`docker-compose.app.yml`** — per-worktree. Brought up **once per worktree**, each with a unique `COMPOSE_PROJECT_NAME` so containers and volumes are namespaced per-worktree. Owns the dev server, ORM Studio, and anything else that should run in parallel copies.

Why split it? Without the split, every worktree would spin up its own Postgres, multiplying memory and storage cost N-way. With the split, all worktrees share one database instance and isolate their writes with per-worktree database names (`WORKTREE_DB`).

If your project will only ever have one developer and one workspace, you can merge the two files at fork time — but the split costs nothing while keeping the worktree door open.

## Opt-in services via Compose profiles

Within each compose file, optional services are gated by `profiles:` so the default `docker compose up` runs only the core. Opt in by activating the profile via the `COMPOSE_PROFILES` env var:

```bash
# Default — only db runs
docker compose -f docker-compose.infra.yml up -d

# With ngrok tunnel
COMPOSE_PROFILES=ngrok docker compose -f docker-compose.infra.yml up -d

# With ORM Studio in the app tier
COMPOSE_PROFILES=studio docker compose -f docker-compose.app.yml --env-file .env.docker up
```

This means a project that doesn't need ngrok or Studio never deletes anything — those services exist in the compose file but never start. Opting in later is a one-env-var flip, no merge conflict next time you re-sync from the template.

## How to use a stamp

**Do not just `cp -r` and edit by hand** — the stamps have placeholder values (`app_shared` network name, Prisma-by-default ORM blocks) that must be substituted for your specific project. Network-name collisions and orphaned ORM scaffolding are silent failures.

Instead, invoke the `new-project-setup` skill from your new project's directory. The skill walks through fork-time decisions (project slug, ORM choice, ngrok yes/no, extra PG extensions) and performs the substitutions in one pass.

If you must do it manually, the per-stamp `README.md` (e.g. `nextjs/README.md`) documents every placeholder and the substitution it needs.

## What ships in every stamp

- A `docker-compose.infra.yml` and `docker-compose.app.yml` with the split described above.
- A `.env.docker.example` listing every `${VAR:?...}` env var the compose files require. Compose's `${VAR:?error}` syntax fails loud on missing values — no silent fallbacks that would let two worktrees collide on the same DB name or port.
- Stamp-specific Dockerfiles for any custom images (typically `Dockerfile.db` for the database and `web/Dockerfile.dev` for the app).
- A stamp-specific `README.md` covering: copy instructions, run order, env-var meanings, profile usage, and ORM-swap recipes where relevant.
