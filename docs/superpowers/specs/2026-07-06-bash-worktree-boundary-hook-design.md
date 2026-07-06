# Bash worktree-boundary guard — design

**Date:** 2026-07-06
**Branch:** `ev-bash-worktree-boundary-hook`
**Status:** approved

## Problem

The existing `hooks/enforce-worktree-boundary.sh` is a `PreToolUse` hook matching
only `Edit|Write|MultiEdit|NotebookEdit`. It keys off `tool_input.file_path` and
blocks edits that resolve to a different git worktree than the session's cwd.

`Bash` is not matched, so file-mutating shell commands sail straight through the
boundary. Observed failure (a worktree agent at
`/Users/eric/code/fitness_tracker/.claude/worktrees/smoke-test/`):

```
cd /Users/eric/code/fitness_tracker && npx prettier --write web/src/lib/rich-text.ts …
```

The agent `cd`'d to the **main** repo root, then used `web/…` relative paths, so
`--write` operated on the main checkout instead of the worktree edits. Here the
main files were already clean so nothing was modified, but the worktree edits
never got formatted and a real mutation would have hit the wrong tree silently.

Two contributing causes:

1. **Mechanical gap** — no `Bash` guard. This spec fixes it.
2. **Ambiguous memory note** — a note reading "run prettier from project root" was
   interpreted as the *main* repo root rather than the worktree root. That note
   lives in the fitness_tracker project's memory, not this template; tighten it
   there separately. Out of scope here.

## Chosen approach: cd-escape guard (hard-block)

Detect the mechanism of harm — a `cd`/`pushd` into a different git worktree —
rather than trying to classify which commands mutate files. Rationale:

- Deterministically catches the observed failure class.
- Near-zero false positives: a worktree session rarely has a legitimate reason to
  `cd` into a *different* worktree.
- **No command allowlist to maintain.** An unmaintained per-tool list is the same
  brittleness class that caused this bug (the next formatter would reopen the gap).

Rejected alternatives:

- **cd-escape + mutating-arg scan** — also scan path args of a curated set
  (`prettier --write`, `eslint --fix`, `sed -i`, `git restore/checkout`,
  `gofmt/black/rustfmt -w`, `rm/mv/cp`, redirects). Catches bare-absolute-path
  mutations too, but the curated list rots. Deferred; layer only if a bare-path
  case actually occurs.
- **Warn instead of block** — lower friction, but the write still happens; does not
  enforce the boundary.

### Accepted limitation

A bare absolute path with no `cd` — e.g. `prettier --write /main/web/...` — is not
caught. Acceptable for v1; revisit only if it occurs in practice.

## Components

### 1. New hook — `hooks/enforce-worktree-boundary-bash.sh`

`PreToolUse`, matcher `Bash`. Reads hook-input JSON on stdin.

Algorithm:

1. `command = .tool_input.command`; empty → `exit 0`.
2. `cwd = .cwd`; empty → `exit 0` (can't determine the boundary).
3. `session_root = git -C "$cwd" rev-parse --show-toplevel`. Empty (cwd not in a
   repo) → `exit 0` (mirrors the edit hook: a session outside a repo is allowed).
4. Extract every `cd`/`pushd` target: the first token after a `cd`/`pushd` that
   begins a command word (after start-of-string, `;`, `&&`, `||`, `|`, `(`, or
   newline). Strip surrounding single/double quotes; expand a leading `~/` to
   `$HOME/`. Skip `cd` with no argument (→ `$HOME`) and `cd -`.
5. For each target, resolve it the way the shell would, relative to the session
   cwd, canonicalizing `..` and symlinks:
   `target_abs=$(cd "$cwd" && cd "$target" && pwd -P)` in a subshell. If that
   `cd` fails (missing dir) → skip the target (the real command would fail anyway).
6. `target_root = git -C "$target_abs" rev-parse --show-toplevel`. Empty (target
   outside any repo, e.g. `/tmp`) → allowed, continue.
7. `target_root != session_root` → **block**: `exit 2` + stderr naming the cd
   target, its tree, the session tree, and remediation (re-run anchored to the
   worktree; bypass via `--dangerously-skip-permissions` or removing the hook).
8. No target trips the check → `exit 0`.

Matches the existing hooks' conventions: `set -euo pipefail`, `jq -r '… // empty'`,
`exit 2` + stderr as the documented `PreToolUse` blocking contract, and the same
stderr tone/format as `enforce-worktree-boundary.sh`.

### 2. Unify the edit hook on `.cwd`

`enforce-worktree-boundary.sh` currently derives the session root from
`CLAUDE_PROJECT_DIR:-$PWD`. Switch it to read input `.cwd` (with
`CLAUDE_PROJECT_DIR:-$PWD` as a fallback if `.cwd` is absent), so both boundary
hooks and `knowledge-reconcile.sh` agree on how the session root is determined.
Behavior is otherwise unchanged.

### 3. Wiring + docs

- `~/.claude/settings.json`: add a `PreToolUse` entry with `"matcher": "Bash"` →
  `$HOME/.claude/hooks/enforce-worktree-boundary-bash.sh`. (User applies this;
  the repo ships no settings.json.)
- `README.md`: add a hooks-table row for the new hook and the new matcher block to
  the install-JSON snippet.

### 4. Test harness — `hooks/test-enforce-worktree-boundary-bash.sh`

Plain bash, no bats dependency. Sets up a temp main repo plus a nested
`git worktree`, pipes crafted hook-input JSON into the hook, asserts exit codes:

| Case                                             | Expect |
| ------------------------------------------------ | ------ |
| `cd <other-worktree> && prettier --write …`      | 2      |
| `cd web && prettier --write src/…` (in-tree)     | 0      |
| command with no `cd`                             | 0      |
| `cd /tmp && …` (outside any repo)                | 0      |
| `cd ..`-escape out of the worktree               | 2      |
| cwd not in a repo                                | 0      |

Runs standalone (`bash hooks/test-enforce-worktree-boundary-bash.sh`); exits
non-zero if any assertion fails.

## Out of scope

- Catching bare-absolute-path mutations without a `cd` (accepted limitation).
- Tightening the fitness_tracker memory note (different repo).
- Any change to `knowledge-reconcile.sh`.
