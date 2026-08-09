#!/usr/bin/env bash
# PreToolUse hook for Edit|Write|MultiEdit|NotebookEdit (pi: write, edit).
#
# Blocks edits whose file_path resolves to a different git worktree
# (`git rev-parse --show-toplevel`) than the session's cwd.
#
# Allowed:  file inside the session's worktree
# Allowed:  file outside any git repo (~/.claude, /tmp, etc.)
# Allowed:  session itself not inside a git repo
# Blocked:  file in a different worktree of the same (or any) repo
#
# This fixes the silent cross-worktree-edit trap: agent runs rg/find
# from a parent dir, gets absolute paths into the main checkout, then
# Edit/Write happily writes into the wrong tree because those tools
# don't validate against cwd.
#
# Exit 2 + stderr is the documented PreToolUse blocking contract.

set -euo pipefail

input=$(cat)
file_path=$(printf '%s' "$input" | jq -r '.tool_input.file_path // empty')
[ -z "$file_path" ] && exit 0

# Session root from the hook-input cwd (same signal as knowledge-reconcile.sh and
# enforce-worktree-boundary-bash.sh); fall back to CLAUDE_PROJECT_DIR/$PWD.
cwd=$(printf '%s' "$input" | jq -r '.cwd // empty')
[ -z "$cwd" ] && cwd="${CLAUDE_PROJECT_DIR:-$PWD}"
session_root=$(git -C "$cwd" rev-parse --show-toplevel 2>/dev/null || true)
[ -z "$session_root" ] && exit 0

file_dir=$(dirname "$file_path")
mkdir -p "$file_dir" 2>/dev/null || true
file_root=$(git -C "$file_dir" rev-parse --show-toplevel 2>/dev/null || true)

[ -z "$file_root" ] && exit 0
[ "$file_root" = "$session_root" ] && exit 0

cat <<EOF >&2
BLOCKED: cross-worktree edit.

  file_path:    $file_path
  file's tree:  $file_root
  session's tree: $session_root

Anchor the path to the session's tree and retry. If you genuinely need
to edit the other tree, do it from a session opened there. Bypass by
unregistering this hook (Claude: ~/.claude/settings.json, pi:
~/.pi/agent/extensions/worktree-boundary.ts).
EOF
exit 2
