#!/usr/bin/env bash
# Test harness for enforce-worktree-boundary-bash.sh.
#
# Builds a throwaway main repo plus a nested `git worktree` (mirroring the real
# .claude/worktrees/<name> layout), pipes crafted PreToolUse hook-input JSON into
# the hook, and asserts the exit code. No bats dependency.
#
# Run:  bash hooks/test-enforce-worktree-boundary-bash.sh
# Exits non-zero if any case fails.

set -uo pipefail

here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
HOOK="$here/enforce-worktree-boundary-bash.sh"

[ -x "$HOOK" ] || { echo "FATAL: hook not found or not executable: $HOOK" >&2; exit 1; }

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

# --- Fixture: main repo with a nested worktree ------------------------------
git -C "$tmp" init -q main
main=$(cd "$tmp/main" && pwd -P)
git -C "$main" -c user.email=t@t -c user.name=t commit -q --allow-empty -m init
git -C "$main" worktree add -q "$main/.claude/worktrees/smoke-test" -b smoke-test
wt=$(cd "$main/.claude/worktrees/smoke-test" && pwd -P)
mkdir -p "$wt/web/src"
nonrepo=$(cd "$tmp" && pwd -P)   # $tmp itself is not a git repo

fails=0
run_case() { # <desc> <cwd> <command> <expected_exit>
  local desc=$1 cwd=$2 cmd=$3 want=$4 got
  local json
  json=$(jq -n --arg cwd "$cwd" --arg cmd "$cmd" \
    '{cwd:$cwd, tool_input:{command:$cmd}}')
  printf '%s' "$json" | bash "$HOOK" >/dev/null 2>&1
  got=$?
  if [ "$got" = "$want" ]; then
    printf 'ok   %s (exit %s)\n' "$desc" "$got"
  else
    printf 'FAIL %s (want %s, got %s)\n' "$desc" "$want" "$got"
    fails=$((fails + 1))
  fi
}

run_case "cd into main worktree then mutate -> block" \
  "$wt" "cd $main && npx prettier --write web/src/x.ts" 2
run_case "cd within own worktree -> allow" \
  "$wt" "cd web && npx prettier --write src/x.ts" 0
run_case "no cd -> allow" \
  "$wt" "npx prettier --write src/x.ts" 0
run_case "cd to non-repo dir -> allow" \
  "$wt" "cd /tmp && ls" 0
run_case "cd .. escapes worktree -> block" \
  "$wt" "cd .. && ls" 2
run_case "session cwd not in a repo -> allow" \
  "$nonrepo" "cd $main && npx prettier --write web/src/x.ts" 0

echo
if [ "$fails" -eq 0 ]; then
  echo "All cases passed."
else
  echo "$fails case(s) failed." >&2
  exit 1
fi
