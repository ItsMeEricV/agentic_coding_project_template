#!/usr/bin/env bash
#
# next-free-port.sh — print the next actually-free host port(s), deterministically.
#
# "Free" means BOTH:
#   1. not published by any Docker container (running OR stopped — `docker ps -a`), and
#   2. not currently bound by any process on the host (covers non-Docker servers too).
#
# Always returns the LOWEST qualifying port >= START. No randomness, no guessing —
# so bootstrapping a new project/worktree never lands on a port that fails to bind.
#
# Usage:
#   ./next-free-port.sh [START] [COUNT]
#
# Examples:
#   ./next-free-port.sh 5432        # next free port for the shared db (>= 5432)
#   ./next-free-port.sh 3000        # next free WEB_PORT (>= 3000)
#   ./next-free-port.sh 5555 2      # two free ports >= 5555 (e.g. STUDIO_PORT pair)
#
# Output: one port per line (COUNT lines).

set -euo pipefail

START="${1:-3000}"
COUNT="${2:-1}"

case "$START" in '' | *[!0-9]*) echo "ERROR: START must be a port number" >&2; exit 1 ;; esac
case "$COUNT" in '' | *[!0-9]*) echo "ERROR: COUNT must be a number" >&2; exit 1 ;; esac

# Host-side ports already published by Docker containers (running + stopped).
# `docker ps -a` Ports column looks like "0.0.0.0:5432->5432/tcp, [::]:5432->5432/tcp";
# we want the host port (left of "->"), never the container port. An exposed-only
# port like "3000/tcp" (no "->") isn't bound on the host, so it's correctly ignored.
docker_used="$(
  { docker ps -a --format '{{.Ports}}' 2>/dev/null || true; } \
    | grep -oE ':[0-9]+->' \
    | tr -dc '0-9\n' \
    | sort -un
)"

# Is $1 bound by any listening process on the host right now?
port_bound() {
  if command -v lsof >/dev/null 2>&1; then
    lsof -nP -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1
  elif command -v nc >/dev/null 2>&1; then
    nc -z 127.0.0.1 "$1" >/dev/null 2>&1
  else
    return 1  # can't probe; assume free (Docker check still applies)
  fi
}

found=0
port="$START"
while [ "$found" -lt "$COUNT" ]; do
  if [ "$port" -gt 65535 ]; then
    echo "ERROR: ran past port 65535 without finding $COUNT free port(s)" >&2
    exit 1
  fi
  if ! printf '%s\n' "$docker_used" | grep -qx "$port" && ! port_bound "$port"; then
    echo "$port"
    found=$((found + 1))
  fi
  port=$((port + 1))
done
