---
name: pull-request-creator
description: Use when creating, updating, or commenting on a GitHub pull request, drafting a PR body, replying to review comments, or resolving review threads.
---

# Creating and Maintaining a Pull Request

## Overview

Every PR Eric creates follows a fixed title format, a fixed body template, and a fixed post-creation workflow. After it opens, every review comment gets attribution and a reply, and resolved threads get closed via GraphQL. This skill is the single source of truth — do not rely on memory of prior conventions.

**Always use the GitHub MCP server (`mcp__github__*`) for PR operations.** Body travels as a JSON field, so no shell, no escaping, no backtick or quote hazards. `gh` is a fallback for operations the MCP doesn't expose (notably `resolveReviewThread`) or when the MCP is unavailable.

**Violating the letter of these rules is violating the spirit.**

## Red Flags — STOP

| Rationalization | Reality |
|---|---|
| "Small change, skip the full template" | Every body section below is mandatory. |
| "I'll just use `gh pr create` real quick" | MCP is the default, not a peer of `gh`. |
| "I'll mark it ready / push to a non-draft PR myself" | Never. Wait for user confirmation. |
| "PR is merged but I have one more fix" | Don't push to a merged branch — start a new branch. |
| "I'll skip `pr-review-toolkit`" | Run it after creation and wait for feedback. |
| "This review comment is obviously wrong" | Reply agree / disagree / defer to **every** comment. |
| "I fixed it, the thread will sort itself out" | Resolve threads explicitly via `resolveReviewThread`. |

## Workflow

1. **Verify branch state.** `git branch --show-current` matches intent. For updates: `mcp__github__pull_request_read` (`method: get`) to confirm the PR isn't merged and isn't already non-draft.

2. **Create via MCP as draft.** Body, title, and everything else pass as JSON — paste markdown verbatim, backticks and quotes included:

   ```
   mcp__github__create_pull_request
     owner, repo, head, base: main, draft: true
     title: "[Feature] description"
     body:  <full markdown body>
   ```

3. **Open in browser:** `gh pr view <N> --web`

4. **Run `pr-review-toolkit`** and wait for user feedback before continuing.

## Title format

`[Feature] - brief description - phase if applicable`

- `[Feature]` — bracketed component, Title Case
- description — lowercase, concise
- phase — optional, multi-phase projects only

Examples: `[Hidden Channels Modal] Logic updates - Phase 5`, `[Search] Improve autocomplete performance`, `[Bugfix] Fix avatar rendering in DM list`

## Body template (all sections, always)

Include every section. If empty, leave placeholder bullets — never omit the section header.

```markdown
**Before this 🐝**
-------

-

**What this PR does 🧑‍💻**
-------

- ✅ Change 1 with detailed explanation
- ✅ Change 2 with context
- ✅ Change 3 with reasoning

**Testing 🧪**
-------

- All unit tests pass
- [Notable new tests, especially toggle on/off coverage]
- pr-review-toolkit was run; high-priority findings were fixed

**Revertable? ♻️**
-------

-

**Risk 🔥**
-------

-

**Notes for Reviewers ✏️**
-------

- **Focus areas**: [what reviewers should pay attention to]
- **Commit-by-commit review**: Each commit is self-contained and can be reviewed individually

**Relevant Links 🔗**
-------

- 💬 **Discussion**: [descriptive title](link)
- 🐛 **Issue / ticket**: [descriptive title](link)
- 📄 **Design doc**: [descriptive title](link)
```

**Rules:** Testing: never mention project-specific build/format commands CI runs automatically, never list individual test names. Links: descriptive text, never naked URLs. Formatting: emoji-after-titles, blank line after each header, no `---` separators, conversational bullets. Files-needing-extra-attention subsection only when genuinely risky.

## Review comments

**Attribute:** prepend `**[CLAUDE]**` to every PR comment and reply you author. Other agents use their own tag (`**[GEMINI]**`, `**[COPILOT]**`) — match `AGENTS.md`.

**Reply to every comment** (human or bot) with one of: **agree** (and fix or open follow-up), **disagree** (and explain), **defer** (link an issue). Silence reads as ignored. Use `mcp__github__add_reply_to_pull_request_comment`.

**Resolve threads** after fixing — leaves the unresolved-count honest. Leave open only what's deferred. The MCP doesn't expose this; use `gh`:

```bash
gh api graphql -f query='
  mutation($threadId: ID!) {
    resolveReviewThread(input: {threadId: $threadId}) {
      thread { id isResolved }
    }
  }' -f threadId="$THREAD_ID"
```

Thread IDs come from `mcp__github__pull_request_read` with `method: get_review_comments`.

If the project wires in an extra automated reviewer (e.g. a Gemini script), invocation is project-specific — see its `AGENTS.md`. For multi-turn reviewer sessions, generate a session UUID up front and pass it on every call.

## Fallback: MCP unavailable

If `mcp__github__*` is missing (different harness, outage), use `gh`. The body-as-shell-arg problem is real **only here** — backticks and embedded quotes need handling:

```bash
# Plain bodies: inline works
gh pr create --draft --title "..." --body "$BODY"

# Bodies with backticks: write to a per-PR file so the shell doesn't eval them.
# Scope filename to this PR (branch pre-creation, PR number after) so parallel
# Claude sessions don't collide on a shared /tmp/pr-body.md.
BRANCH=$(git branch --show-current)
cat > "/tmp/pr-body-${BRANCH}.md" <<'EOF'
...body with `backticks` and 'quotes'...
EOF
gh pr create --draft --title "..." --body-file "/tmp/pr-body-${BRANCH}.md"
```
