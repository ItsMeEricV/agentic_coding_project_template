---
name: handoff
description: Compact the current conversation into a handoff document for another agent to pick up.
argument-hint: 'What will the next session be used for?'
---

Write a handoff document summarising the current conversation so a fresh agent can continue the work.

Pick a short kebab-case slug (2–5 words) describing the handoff's focus, derived from the user's argument or the conversation. Save the doc to:

    /tmp/handoff-$(date +%Y%m%d)-<slug>.md

The `Write` tool creates the file when the path does not exist, so no prior `Read` is needed. Example: `/tmp/handoff-20260516-fitness-tracker-cli-migration.md`. The date prefix keeps multiple handoffs chronologically sortable; the slug makes the file's purpose obvious from `ls`.

After writing the file, **print the path as the final line of your response** so the user can hand it to the next session without hunting for it. Also copy it to the clipboard on platforms where `pbcopy` is available:

    command -v pbcopy >/dev/null && printf %s "<path>" | pbcopy

The `command -v` check skips silently on Linux / non-macOS where `pbcopy` isn't installed, so this is safe to always run.

Suggest the skills to be used, if any, by the next session.

Do not duplicate content already captured in other artifacts (PRDs, plans, ADRs, issues, commits, diffs). Reference them by path or URL instead.

If the user passed arguments, treat them as a description of what the next session will focus on and tailor the doc accordingly.
