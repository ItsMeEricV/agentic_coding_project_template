# Next.js Stamp

Drop-in Docker dev stack for Next.js + PostgreSQL 18 + pgvector + Prisma (default). Supports multi-agent worktree development out of the box.

## What's in this stamp

```
docker-compose.infra.yml    # db (always) + ngrok (profile-gated). Brought up once per machine.
docker-compose.app.yml      # web (always) + studio (profile-gated). Brought up once per worktree.
Dockerfile.db               # PG18 + pgvector (single-stage)
.env.docker.example         # required env vars per worktree
web/
  Dockerfile.dev            # Node 24 + Prisma (default, ORM-fenced for swaps)
  .dockerignore
```

## Bootstrap

**Prefer the `new-project-setup` skill** — it walks through fork-time decisions (project slug, ORM choice, ngrok yes/no, extras) and performs substitutions in one batch. Manual instructions below for reference.

### 1. Copy the stamp to your project root

```bash
cp -a path/to/agentic_coding_project_template/docker/nextjs/. .
```

The trailing `/.` is load-bearing — `nextjs/*` would skip dotfiles like `.env.docker.example` and `web/.dockerignore`. `cp -a` preserves the directory layout (compose files at the project root, the DB Dockerfile next to them, the dev Dockerfile under `web/`).

### 2. Substitute placeholders

| Placeholder         | Where                                                | Replace with                                                                                                                            |
| ------------------- | ---------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| `app_shared`        | `docker-compose.infra.yml`, `docker-compose.app.yml` | `<your-project-slug>_shared` — must match in both files                                                                                 |
| `app_db`            | `docker-compose.infra.yml` (`container_name`)        | `<your-project-slug>_db` — keeps multiple projects on the same daemon from colliding on container name                                  |
| `"5432:5432"`       | `docker-compose.infra.yml` (db `ports`)              | Change the **host** side (left of `:`) if 5432 is already in use on this machine — e.g. `"5433:5432"`. Container side must stay `5432`. |
| `app_dev`           | `docker-compose.infra.yml` (`POSTGRES_DB`)           | Your default DB name                                                                                                                    |
| `YOUR_NGROK_DOMAIN` | `docker-compose.infra.yml` (ngrok `command`)         | Your reserved ngrok hostname; only needed if enabling the `ngrok` profile                                                               |

Note: the network alias `db` stays unchanged regardless of `container_name` — the app stack always uses `db:5432` internally via the `aliases:` block on the db service.

### 3. Configure your worktree

```bash
cp .env.docker.example .env.docker
# Edit .env.docker — at minimum, set WEB_PORT, STUDIO_PORT, WORKTREE_DB,
# COMPOSE_PROJECT_NAME to values unique to this worktree.
```

### 4. Bring it up

```bash
# Once per machine — shared infra. The --env-file flag is required so
# COMPOSE_PROFILES (and NGROK_AUTHTOKEN, if enabling ngrok) is read; per-worktree
# vars in .env.docker are harmlessly ignored by infra services.
docker compose -f docker-compose.infra.yml --env-file .env.docker up -d

# Once per worktree — app stack
docker compose -f docker-compose.app.yml --env-file .env.docker up
```

App at `http://127.0.0.1:${WEB_PORT}`. Studio (if enabled) at `http://localhost:${STUDIO_PORT}`. ngrok inspector (if enabled) at `http://localhost:4040`.

## Profiles

Optional services are gated by Compose profiles. Activate them via the `COMPOSE_PROFILES` env var:

| Profile  | Service                  | Tier  |
| -------- | ------------------------ | ----- |
| `ngrok`  | Public dev-server tunnel | infra |
| `studio` | Prisma/Drizzle Studio    | app   |

```bash
# Enable studio for this worktree (set in .env.docker, then `up`)
COMPOSE_PROFILES=studio docker compose -f docker-compose.app.yml --env-file .env.docker up

# Or set persistently in .env.docker:
echo 'COMPOSE_PROFILES=studio,ngrok' >> .env.docker
```

## Swapping ORMs

The Prisma-coupled lines in `docker-compose.app.yml` and `web/Dockerfile.dev` are visually fenced:

```
# --- ORM: Prisma ---
...
# --- /ORM ---
```

To swap, replace what's between the fences. The fences themselves act as markers so future-you can find every touch point.

### Drizzle

**`docker-compose.app.yml`** — replace the fenced `studio:` block with:

```yaml
# --- ORM: Drizzle ---
studio:
  profiles: [studio]
  build:
    context: ./web
    dockerfile: Dockerfile.dev
  ports:
    - "${STUDIO_PORT:?STUDIO_PORT is required — set it in .env.docker}:4983"
  environment:
    - DATABASE_URL=postgresql://postgres:postgres@db:5432/${WORKTREE_DB}
  networks:
    - app_shared
  command: npx drizzle-kit studio --port 4983 --host 0.0.0.0
  deploy:
    resources:
      limits:
        memory: 500m
# --- /ORM ---
```

**`web/Dockerfile.dev`** — replace the three fenced blocks with:

```dockerfile
# --- ORM: Drizzle --- (schema is plain TS, picked up by `COPY . .` — no extra COPY)
# --- /ORM ---
```

```dockerfile
# --- ORM: Drizzle --- (no codegen — Drizzle infers types from schema TS at build/edit time)
# --- /ORM ---
```

```dockerfile
# --- ORM: Drizzle ---
CMD ["sh", "-c", "npx drizzle-kit migrate && npm run dev"]
# --- /ORM ---
```

### No ORM / other

Delete or comment out the `studio:` service entirely. In `web/Dockerfile.dev`, remove the Prisma-specific COPY, generate-step, and migrate-on-start command — replace the final fenced block with a plain `CMD ["npm", "run", "dev"]`.

## The worktree pattern

The infra/app split is sized for multi-agent or multi-worktree dev:

- One **shared** Postgres serves all worktrees. Each worktree writes to its own `WORKTREE_DB` (a database inside the shared instance) so writes are isolated.
- Each worktree gets a **unique** `WEB_PORT` and `STUDIO_PORT` so dev servers don't collide.
- `COMPOSE_PROJECT_NAME` namespaces Docker containers, volumes, and Auth-cookie names per worktree.
- ngrok (when enabled) tunnels to a fixed host port (3000 by default); the worktree publishing that port wins the public URL.

If your project will only ever have one workspace, you can run with the split as-is — the second worktree just never gets created. The split costs nothing while keeping the door open.

## Notes

- **PG18 native UUIDv7.** Use `uuidv7()` in raw SQL (migrations, webhooks, scripts) — not `gen_random_uuid()` (UUIDv4) and not `uuid_generate_v7()` (the PG14-17 extension function name). Prisma users: `@default(uuid(7))` generates UUIDv7 client-side and is preferred for application code.
- **Rebuilds after dep changes.** After editing `package.json`/lockfile or any Dockerfile, rebuild with `-V` to recreate volumes: `docker compose -f docker-compose.app.yml --env-file .env.docker up -d --build -V web`. Without `-V`, the named `web_node_modules` volume is reused and your new packages won't be there.
- **`docker compose restart` does not re-read env files.** Use `up -d` to recreate the container with updated env vars.
