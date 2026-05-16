#!/usr/bin/env bash
# worktree-add.sh — create a new git worktree wired up for the project's
# Docker stack (per-worktree ports, db name, COMPOSE_PROJECT_NAME).
#
# Usage:
#   ./cli/worktree-add.sh <name>            # creates ../<name>, branch <name>
#   ./cli/worktree-add.sh <name> <branch>   # creates ../<name>, branch <branch>
#
# What it does:
#   1. `git worktree add ../<name> -b <branch>` (or attaches to existing branch)
#   2. Copies .env.docker.example → ../<name>/.env.docker
#   3. Substitutes per-worktree values:
#        WEB_PORT     = 3000 + N
#        STUDIO_PORT  = 5555 + N
#        WORKTREE_DB  = <base>_dev_<name>
#        COMPOSE_PROJECT_NAME = <base>-<name>
#      where N is the count of existing git worktrees (so first new worktree
#      gets +1, second gets +2, etc.).
#   4. Prints the bring-up commands for the new worktree.
#
# Assumes:
#   - Run from the root of the main worktree
#   - .env.docker.example exists at the root (per docker/nextjs/ stamp)
#   - The shared infra stack is already up (or the user will start it)

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <name> [branch]" >&2
  echo "  name    — short identifier for the worktree (becomes the directory name)" >&2
  echo "  branch  — git branch name (default: same as <name>)" >&2
  exit 64
fi

name=$1
branch=${2:-$name}

if [[ ! -f .env.docker.example ]]; then
  echo "error: .env.docker.example not found in $(pwd)" >&2
  echo "  Run this script from the root of the main worktree (where the Docker stamp was applied)." >&2
  exit 65
fi

# Count existing worktrees (each `worktree <path>` line in `git worktree list --porcelain`).
n=$(git worktree list --porcelain | grep -c '^worktree ')

# Derive the project base from COMPOSE_PROJECT_NAME in .env.docker.example.
# Expected default: `<base>-main` → base = everything before `-main`.
default_cpn=$(grep -E '^COMPOSE_PROJECT_NAME=' .env.docker.example | head -n1 | cut -d= -f2-)
if [[ -z $default_cpn ]]; then
  echo "error: COMPOSE_PROJECT_NAME not found in .env.docker.example" >&2
  exit 66
fi
base=${default_cpn%-main}
# Same logic for WORKTREE_DB: default is <base_db>_dev_main → base_db = everything before _dev_main
default_db=$(grep -E '^WORKTREE_DB=' .env.docker.example | head -n1 | cut -d= -f2-)
db_base=${default_db%_dev_main}

new_web_port=$((3000 + n))
new_studio_port=$((5555 + n))
new_worktree_db="${db_base}_dev_${name}"
new_cpn="${base}-${name}"

target_dir="../${name}"

if [[ -e $target_dir ]]; then
  echo "error: $target_dir already exists" >&2
  exit 67
fi

# Create the worktree. If the branch already exists, attach to it; otherwise create it.
if git show-ref --verify --quiet "refs/heads/${branch}"; then
  git worktree add "$target_dir" "$branch"
else
  git worktree add -b "$branch" "$target_dir"
fi

# Generate the worktree's .env.docker by substituting into the example.
sed \
  -e "s|^WEB_PORT=.*|WEB_PORT=${new_web_port}|" \
  -e "s|^STUDIO_PORT=.*|STUDIO_PORT=${new_studio_port}|" \
  -e "s|^WORKTREE_DB=.*|WORKTREE_DB=${new_worktree_db}|" \
  -e "s|^COMPOSE_PROJECT_NAME=.*|COMPOSE_PROJECT_NAME=${new_cpn}|" \
  .env.docker.example > "${target_dir}/.env.docker"

cat <<EOF

✓ Worktree created at ${target_dir}
  branch:                ${branch}
  WEB_PORT:              ${new_web_port}
  STUDIO_PORT:           ${new_studio_port}
  WORKTREE_DB:           ${new_worktree_db}
  COMPOSE_PROJECT_NAME:  ${new_cpn}

Bring it up:
  cd ${target_dir}
  docker compose -f docker-compose.app.yml --env-file .env.docker up

(Shared infra should already be running — if not, from any worktree:
  docker compose -f docker-compose.infra.yml --env-file .env.docker up -d)
EOF
