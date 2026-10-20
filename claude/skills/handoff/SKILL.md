---
name: handoff
description: Compact the current conversation into a handoff document for another agent to pick up.
argument-hint: 'What will the next session be used for?'
---

Write a handoff document summarising the current conversation so a fresh agent can continue the work.

Pick a short kebab-case slug (2–5 words) describing the handoff's focus, derived from the user's argument or the conversation. Then prepare the directory and get the path:

    dir="$(git rev-parse --show-toplevel 2>/dev/null || pwd)/.handoffs"
    mkdir -p "$dir" && printf '*\n' > "$dir/.gitignore"
    find "$dir" -name 'handoff-*.md' -mtime +14 -delete
    echo "$dir/handoff-$(date +%Y%m%d)-<slug>.md"

Write the doc to the printed path with your file-writing tool; a new file needs no prior read. Example: `~/code/app/.handoffs/handoff-20260516-fitness-tracker-cli-migration.md`. The date prefix keeps multiple handoffs chronologically sortable; the slug makes the file's purpose obvious from `ls`.

Why there, and not `/tmp` (cleared at reboot) or `.git/` (write-protected in Claude Code and Codex):

- **The session's worktree is the one place every harness writes without a prompt.** Never `cd` elsewhere to write it; the worktree-boundary hooks block that.
- **The `*` in `.handoffs/.gitignore` keeps the folder out of git** in any repo, with no entry in the project's own `.gitignore`.
- **It cleans itself up.** A handoff nobody picked up in two weeks is stale, so each write deletes those; removing the worktree removes the rest.

After writing the file, **print the path as the final line of your response** so the user can hand it to the next session without hunting for it. Also copy a ready-to-paste prompt to the clipboard on platforms where `pbcopy` is available:

    command -v pbcopy >/dev/null && printf %s "look at <path> and implement" | pbcopy

The clipboard payload is the full phrase `look at <path> and implement` (not just the path) so the user can paste it directly into the next session without retyping. The `command -v` check skips silently on Linux / non-macOS where `pbcopy` isn't installed, so this is safe to always run.

Do not duplicate content already captured in other artifacts (PRDs, plans, ADRs, issues, commits, diffs). Reference them by path or URL instead.

If the user passed arguments, treat them as a description of what the next session will focus on and tailor the doc accordingly.
