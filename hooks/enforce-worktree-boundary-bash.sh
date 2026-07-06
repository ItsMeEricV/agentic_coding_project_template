#!/usr/bin/env bash
# PreToolUse hook for Bash.
#
# Blocks a shell command that `cd`/`pushd`es into a DIFFERENT git worktree than
# the session's cwd. This is the Bash-side companion to
# enforce-worktree-boundary.sh (which guards the Edit/Write tools).
#
# The trap it closes: a worktree agent runs
#   cd /path/to/main-checkout && npx prettier --write web/src/foo.ts
# so the mutating command operates on the main checkout, not the worktree edits,
# silently. The edit-tool hook never sees this because it's a Bash call.
#
# Detection is on the mechanism of harm (a cd/pushd escaping the worktree), not
# on classifying which commands mutate files — so there's no per-tool allowlist
# to fall out of date. Reads elsewhere, /tmp, and non-repo dirs are allowed.
#
# Allowed:  no cd/pushd, or all cd targets stay in the session's worktree
# Allowed:  cd into a dir outside any git repo (/tmp, ~/scratch, ...)
# Allowed:  session cwd not inside a git repo
# Blocked:  cd/pushd into a different worktree (of the same or any repo)
#
# Not caught (accepted limitation): a bare absolute path with no cd, e.g.
# `prettier --write /main/web/foo.ts`. Layer that only if it occurs in practice.
#
# Exit 2 + stderr is the documented PreToolUse blocking contract.

set -euo pipefail

input=$(cat)
command=$(printf '%s' "$input" | jq -r '.tool_input.command // empty')
[ -z "$command" ] && exit 0

cwd=$(printf '%s' "$input" | jq -r '.cwd // empty')
[ -z "$cwd" ] && cwd="${CLAUDE_PROJECT_DIR:-$PWD}"

session_root=$(git -C "$cwd" rev-parse --show-toplevel 2>/dev/null || true)
[ -z "$session_root" ] && exit 0

# Split the command into segments on shell separators (;  &  &&  ||  |  ( and
# newlines), so each cd/pushd sits at the start of its own segment.
segments=$(printf '%s\n' "$command" | sed -E 's/(&&|\|\||[;&|(])/\n/g')

while IFS= read -r seg; do
  # Trim leading whitespace.
  seg="${seg#"${seg%%[![:space:]]*}"}"
  case "$seg" in
    cd|pushd) continue ;;                # bare cd -> $HOME; nothing to check
    cd[[:space:]]*|pushd[[:space:]]*) : ;;
    *) continue ;;
  esac

  # First non-flag token after the keyword is the target directory.
  read -ra words <<< "$seg"
  i=1
  while [ "$i" -lt "${#words[@]}" ] && [[ ${words[$i]} == -* ]]; do i=$((i + 1)); done
  target=${words[$i]:-}
  [ -z "$target" ] && continue           # `cd -` / `cd --` etc.

  # Strip one layer of surrounding quotes; expand a leading ~.
  target="${target%\"}"; target="${target#\"}"
  target="${target%\'}"; target="${target#\'}"
  case "$target" in
    "~") target="$HOME" ;;
    "~/"*) target="$HOME/${target#\~/}" ;;
  esac

  # Resolve as the shell would (relative to cwd, canonicalizing .. and symlinks).
  # If the cd would fail (missing dir), skip — the real command would fail too.
  target_abs=$(cd "$cwd" 2>/dev/null && cd "$target" 2>/dev/null && pwd -P) || true
  [ -z "$target_abs" ] && continue

  target_root=$(git -C "$target_abs" rev-parse --show-toplevel 2>/dev/null || true)
  [ -z "$target_root" ] && continue      # target outside any repo -> allowed
  [ "$target_root" = "$session_root" ] && continue

  cat <<EOF >&2
BLOCKED: cross-worktree Bash command.

  cd target:      $target  ->  $target_abs
  target's tree:  $target_root
  session's tree: $session_root

This command changes directory into a different git worktree, so anything it
writes lands in the wrong checkout. Re-run it anchored to the session's worktree
($session_root) instead of cd-ing out. Bypass: disable the hook in
~/.claude/settings.json or rerun with --dangerously-skip-permissions.
EOF
  exit 2
done <<< "$segments"

exit 0
