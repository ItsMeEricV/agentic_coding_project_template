# Worktree commands

The rules are in SKILL.md, "Worktrees". This file is the commands. `<main>` is the main checkout, `<path>` a worktree, `<branch>` its branch.

## Start a ticket worktree

```bash
git -C <main> fetch origin
git -C <main> worktree add -b <branch> <path> origin/main
```

Put the path and branch in the handoff. The session runs the project's install step in its own worktree; it never `cd`s into another.

## Keep tools out of other worktrees

Subagent worktrees sit inside the main checkout, at `.claude/worktrees/<name>`. A tool that globs from the repo root walks into every one of them: each is a full copy of the repo, often with its own `node_modules`. One lint run over 16 of them (20 GB) ran out of memory at 4 GB.

Every config that walks the tree ignores `.claude/`. Check each one the project has, for example:

| Tool                    | Where the ignore goes                                            |
| ----------------------- | ---------------------------------------------------------------- |
| ESLint (flat config)    | `ignores: [".claude/**"]` in a global ignores object             |
| Prettier                | `.prettierignore`                                                |
| Vitest / Jest           | `exclude` / `testPathIgnorePatterns`                             |
| TypeScript              | `exclude` in each `tsconfig.json` that uses a broad `include`    |
| Biome, Ruff, pytest, Go | their exclude setting; `go` skips dirs starting with `.` already |

`.gitignore` alone doesn't do it: many tools don't read it. To test, create a worktree with the Agent tool, run the project's check from `<main>`, and confirm no path under `.claude/` shows up.

## Share dependencies with subagent worktrees

Claude Code's `worktree.symlinkDirectories` setting (in `settings.json`) symlinks the named directories from the main checkout into each worktree Claude Code creates (the Agent tool's `isolation: "worktree"`, `EnterWorktree`). Nothing is symlinked by default. It skips absolute paths, `..` traversal, and a source that doesn't exist.

```json
{ "worktree": { "symlinkDirectories": ["node_modules"] } }
```

Caveats before recommending it:

- It doesn't apply to worktrees you make with `git worktree add`; ticket worktrees still install.
- Only the listed paths are linked. A workspace monorepo with per-package `node_modules` (pnpm, yarn workspaces) needs each one listed, or the subagent still installs.
- An install inside the worktree writes through the link into the main checkout's dependencies. Fine when the task doesn't change dependencies; wrong when it does: that task installs normally.
- `worktree.sparsePaths` (git sparse-checkout, cone mode) shrinks the checkout itself in a large monorepo.

Editing `settings.json` is the user's step (the classifier blocks it): hand them the snippet.

## Remove a subagent worktree (the ticket session)

After the task's branch is merged into the ticket branch:

```bash
git -C <main> merge-base --is-ancestor <task-branch> <ticket-branch> && echo merged
git -C <main> worktree remove <path>          # refuses if dirty: good
git -C <main> branch -d <task-branch>         # refuses if unmerged: good
```

## Remove a ticket worktree (the coordinator)

After its PR merged and its session stood down:

```bash
git -C <path> status --porcelain              # empty = clean
git -C <main> fetch origin
git -C <main> cherry origin/main <branch>     # lines starting "+" = commits not on main
git -C <main> worktree remove <path>
git -C <main> branch -d <branch>
```

`git cherry` compares patches, so it sees commits that landed through a squash or rebase merge as present (`-`) when the patch is unchanged. A merge-commit PR leaves `git branch -d` happy on its own. If `-d` refuses after a squash merge and `git cherry` shows only `-` lines, the commits are on main: ask the user for `git branch -D <branch>`. The remote branch (`git push origin --delete <branch>`) is the user's call too.

Merge the PR without `--delete-branch` (`gh pr merge <n> --squash`): that flag also removes the worktree the branch is checked out in, under a live session. The branch goes in this cleanup.

Removing a worktree deletes the directory only. Its branch and commits stay, so a removed worktree can be recreated with `git worktree add <path> <branch>`.

## Heartbeat sweep

```bash
git -C <main> fetch origin --prune
git -C <main> worktree list --porcelain
```

For each worktree other than `<main>`, in order:

1. A live session still runs there (`ListAgents` cwd, or its terminal workspace) → keep.
2. `git -C <path> status --porcelain` is non-empty → keep; report "dirty".
3. `git -C <main> cherry origin/main <branch>` has `+` lines → keep; report "N commits not on main" (unpushed or unmerged work).
4. Otherwise → `git worktree remove <path>` and `git branch -d <branch>`.

Report one line: removed, kept with reasons. Entries whose directory is already gone show as `prunable`; `git worktree prune` clears them, on the user's yes.
