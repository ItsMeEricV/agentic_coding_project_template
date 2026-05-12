---
name: pull-request-creator
description: Use when creating a GitHub pull request with `gh pr create`, drafting/updating a PR body, replying to review comments, or resolving review threads. Enforces PR title format, mandatory body template, draft+browser+pr-review-toolkit workflow, comment attribution conventions, and safe shell quoting for bodies containing backticks.
---

# Creating and Maintaining a Pull Request

## Overview

Every PR Eric creates follows a fixed title format, a fixed body template, and a fixed post-creation workflow (draft → browser → pr-review-toolkit). Once the PR is open, every review comment gets attribution and a reply, and resolved threads get closed via GraphQL. This skill is the single source of truth — **do not rely on memory of prior conventions**.

## Red Flags — STOP if you catch yourself doing these

| Rationalization | Reality |
|---|---|
| "This change is small, I don't need the full template" | All **Required body sections** below are mandatory regardless of change size. |
| "I'll merge `origin/master` first since reviewers have already started" | Only after PR is marked ready for review. If still draft, **rebase** onto `origin/master` for clean history. |
| "I'll push now and mark it ready myself" | Never mark a PR ready for review. Never push to a non-draft PR without explicit user confirmation. |
| "The PR is already merged, but I have one more fix to push" | **Do not push to a merged PR's branch.** It recreates the branch on remote. Start a new branch. |
| "I'll use a heredoc for the body since it has backticks" | Heredocs can misinterpret backticks. Use `--body-file` with a per-PR filename (see "Body file naming" below) or a single-quoted variable with escaped quotes. |
| "I'll reuse `/tmp/pr-body.md` since it's already there" | **Never use a shared filename.** It collides with other Claude sessions and silently picks up a stale body from a prior PR. Always scope the filename to this PR (branch name while creating, PR number afterward). |
| "I'll skip pr-review-toolkit, the PR looks good" | Always run `pr-review-toolkit` after creation and wait for user feedback before continuing. |
| "This review comment is obviously wrong, I'll just ignore it" | Reply to **every** review comment with agree / disagree / defer. Silence reads as ignored. |
| "I fixed the issue, the thread will sort itself out" | Resolve the thread explicitly via GraphQL `resolveReviewThread`. Leave open only what's deferred. |

## Workflow

1. **Verify branch state** before anything:
   - `git branch --show-current` matches intended branch
   - PR branch (if updating) is not merged — `gh pr view <N> --json state`
   - If updating an existing PR, check draft status — do NOT push to a non-draft PR without user confirmation

2. **Write body to a per-PR file** (avoids all shell-quoting issues with backticks / single quotes, and never clobbers another session's in-flight body):

   **Creating a new PR** — use the current branch name in the filename, since the PR number doesn't exist yet:
   ```bash
   BRANCH=$(git branch --show-current)
   BODY_FILE="/tmp/pr-body-${BRANCH}.md"
   cat > "$BODY_FILE" <<'EOF'
   ...body content...
   EOF
   gh pr create --draft --title "[Feature] description" --body-file "$BODY_FILE"

   # Immediately rename to the PR-number-scoped file so future updates target the canonical name
   PR_NUM=$(gh pr view --json number --jq .number)
   mv "$BODY_FILE" "/tmp/pr-body-${PR_NUM}.md"
   ```

   **Updating an existing PR** — use the PR number directly:
   ```bash
   PR_NUM=<N>
   BODY_FILE="/tmp/pr-body-${PR_NUM}.md"
   cat > "$BODY_FILE" <<'EOF'
   ...body content...
   EOF
   gh pr edit "$PR_NUM" --body-file "$BODY_FILE"
   ```

3. **Create as draft** and open in browser:
   ```bash
   gh pr view --web
   ```

4. **Run pr-review-toolkit** on the PR and wait for user feedback before continuing.

## Title format

```
[Feature] - brief description of changes - phase if applicable
```

- **[Feature]**: bracketed feature/component name, Title Case
- **Brief description**: lowercase, concise
- **Phase**: optional (include for multi-phase projects)

Examples:
- `[Hidden Channels Modal] Logic updates - Phase 5`
- `[Search] Improve autocomplete performance`
- `[Bugfix] Fix avatar rendering in DM list`

## Required body sections (ALL of these, always)

Include **every** section below. If a section has no content yet, include it with placeholders — do not omit. The only thing that's optional is the *content* of some subsections (e.g. `Files needing extra attention`), not the top-level sections themselves.

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
- [Notable new unit/integration tests added, especially toggle on/off coverage]
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

### Section rules

- **Testing**: NEVER mention project-specific build/format commands that CI runs automatically (e.g. linters, formatters, codegen). NEVER mention individual test names; just say "All unit tests pass."
- **Notes for Reviewers → Files needing extra attention**: only include this subsection when there are genuinely risky/large files.
- **Links**: always use descriptive link text, never naked URLs.

### Formatting rules

- Emoji after section titles (as shown)
- Blank line after each header before content
- NO `---` separator lines between sections
- Use conversational, detailed bullets

## Body file naming

**Never write to a shared filename like `/tmp/pr-body.md`.** Multiple Claude sessions run in parallel and a stale file from a previous PR will silently be reused. Always scope the filename to *this* PR:

- **Before the PR exists**: use the branch name — `/tmp/pr-body-${BRANCH}.md`
- **After creation / when updating**: use the PR number — `/tmp/pr-body-${PR_NUM}.md`
- Rename from branch-scoped → PR-number-scoped immediately after `gh pr create` succeeds, so future edits in the same session (or later sessions) find the canonical file.

The PR-number file persists on disk; that's intentional — if you come back later to add something, the prior body is exactly where you left it. Just rewrite the file from scratch rather than appending, unless the user explicitly asks to amend.

## Shell quoting for PR bodies

Backticks in bodies (code references, inline snippets) are the #1 source of broken PRs. Pick one of:

```bash
# Best — write body to a per-PR file
BODY_FILE="/tmp/pr-body-$(git branch --show-current).md"
cat > "$BODY_FILE" <<'EOF'
Body with `backticks` and it's safe
EOF
gh pr create --draft --title "..." --body-file "$BODY_FILE"

# Also fine — single-quoted variable, escape apostrophes with '"'"'
PR_BODY='Body with `backticks` and it'"'"'s safe'
gh pr create --draft --title "..." --body "$PR_BODY"

# Avoid — $(cat <<'EOF' …) can still misinterpret backticks in some shells
```

## Review comments: attribution

Always prepend `**[CLAUDE]**` to PR comments and review replies you author, so they're visually separable from human and other-bot comments at a glance.

Other agents in the same repo should use their own tag (e.g. `**[GEMINI]**`, `**[COPILOT]**`). Match whatever convention the project's `AGENTS.md` documents.

## Review comments: responding

Reply to **every** review comment (human or bot) with one of three assessments:

- **Agree** — and either fix in this PR or open a follow-up issue.
- **Disagree** — and explain why, briefly.
- **Defer** — acknowledge it's worth doing, but not in this PR; link an issue if one exists.

Don't leave review comments hanging. Silence reads as "ignored."

Prefer the GitHub MCP server (`mcp__github__add_reply_to_pull_request_comment`) for replies. Fall back to `gh api repos/{owner}/{repo}/pulls/{pr}/comments/{id}/replies` when the MCP isn't available.

## Resolving review threads

After fixing an issue raised in a review comment, **resolve the thread** so the PR's unresolved-count reflects reality. Leave threads open for acknowledged-but-deferred items — they serve as a checklist.

Resolution goes through GitHub's GraphQL `resolveReviewThread` mutation (the REST API does not expose this):

```bash
gh api graphql -f query='
  mutation($threadId: ID!) {
    resolveReviewThread(input: {threadId: $threadId}) {
      thread { id isResolved }
    }
  }' -f threadId="$THREAD_ID"
```

Get thread IDs from the PR's review threads via `gh api graphql` with a query on `pullRequest.reviewThreads`.

## Project-specific automated reviewers

Some projects wire in an additional automated reviewer beyond `pr-review-toolkit` (e.g. a Gemini reviewer script). Invocation is project-specific — see the project's `AGENTS.md`.

For multi-turn reviewer sessions, generate a session UUID at the start and pass it on every subsequent call. This scopes conversation history to the current PR and prevents stale context from earlier reviews leaking in.

## Common mistakes

| Mistake | Fix |
|---|---|
| Used naked URL in Links section | Wrap in descriptive link text |
| Mentioned project-specific build/format commands in Testing | Delete — CI runs these |
| Listed individual test names in Testing | Replace with "All unit tests pass" |
| Used `--body "$(cat <<EOF...)"` with backticks in body | Use `--body-file "/tmp/pr-body-${BRANCH_OR_PR_NUM}.md"` instead |
| Wrote body to shared `/tmp/pr-body.md` | Scope to this PR: `/tmp/pr-body-${BRANCH}.md` while creating, `/tmp/pr-body-${PR_NUM}.md` after |
| Created PR non-draft | Always pass `--draft` |
| Skipped `pr-review-toolkit` run | Run it and wait for user feedback |
| Forgot to open PR in browser | `gh pr view --web` immediately after creation |
| Left a review comment unanswered | Reply agree / disagree / defer to every comment |
| Forgot to resolve a thread after fixing | `gh api graphql … resolveReviewThread` |
