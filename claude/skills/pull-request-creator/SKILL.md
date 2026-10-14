---
name: pull-request-creator
description: Use when creating, updating, or commenting on a GitHub pull request, drafting a PR body, writing the "What to Watch" production-monitoring block, or replying to review comments. Also use when a loop agent needs to read a PR's What to Watch block to judge a deploy.
---

# Creating and Maintaining a Pull Request

## Overview

Every PR follows a fixed title format, a fixed body template, and a fixed post-creation workflow. After it opens, every review comment gets attribution and a reply. This skill is the single source of truth — do not rely on memory of prior conventions.

**Always use the GitHub MCP server (`mcp__github__*`) for PR operations.** Body travels as a JSON field, so no shell, no escaping, no backtick or quote hazards. `gh` is a fallback for operations the MCP doesn't expose or when the MCP is unavailable.

**Violating the letter of these rules is violating the spirit.**

## Red Flags — STOP

| Rationalization                                              | Reality                                                                                                |
| ------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------ |
| "Small change, skip the full template"                       | Every body section below is mandatory.                                                                 |
| "I'll just use `gh pr create` real quick"                    | MCP is the default, not a peer of `gh`.                                                                |
| "I'll mark a draft PR ready / push to a non-draft PR myself" | Never. Wait for user confirmation.                                                                     |
| "PR is merged but I have one more fix"                       | Don't push to a merged branch — start a new branch.                                                    |
| "I'll skip `pr-review-toolkit`"                              | Run it after creation and wait for feedback — unless the PR qualifies as simple (see Workflow step 5). |
| "This review comment is obviously wrong"                     | Reply agree / disagree / defer to **every** comment.                                                   |
| "I'll put a plausible threshold in What to Watch"            | A guessed number is worse than `watch: none`. Another agent acts on it.                                |
| "The alert route isn't wired but I'll open the PR anyway"    | Preflight failure is a hard stop. See [references/what-to-watch.md](references/what-to-watch.md).      |

## Workflow

1. **Verify branch state.** `git branch --show-current` matches intent. For updates: `mcp__github__pull_request_read` (`method: get`) to confirm the PR isn't merged and isn't already non-draft.

2. **Preflight What to Watch.** Resolve the alert route and observability sources, verify the tools exist in this session, and derive the items from the diff. Procedure and schema: [references/what-to-watch.md](references/what-to-watch.md). A declared-but-unreachable route or source stops the workflow here — the PR does not open until the user fixes the wiring or changes the declaration.

3. **Create via MCP.** Body, title, and everything else pass as JSON — paste markdown verbatim, backticks and quotes included. **Default to `draft: true`** unless the project's `CLAUDE.md` or `AGENTS.md` specifies otherwise.

   ```
   mcp__github__create_pull_request
     owner, repo, head, base: main, draft: <per project policy>
     title: "[Feature] description"
     body:  <full markdown body>
   ```

4. **Open in browser:** `gh pr view <N> --web`

5. **Run `pr-review-toolkit`** and wait for user feedback before continuing. **Skip on simple PRs** — token cost outweighs signal. A PR is "simple" if any of these hold: docs/`.md`-only changes, tests-only changes, or under 500 lines of code changed. When skipping, also drop the "pr-review-toolkit was run" line from the Testing section.

## Title format

`[Feature] - brief description - phase if applicable`

- `[Feature]` — bracketed component, Title Case
- description — lowercase, concise
- phase — optional, multi-phase projects only

Examples: `[Hidden Channels Modal] Logic updates - Phase 5`, `[Search] Improve autocomplete performance`, `[Bugfix] Fix avatar rendering in DM list`

## Body template (all sections, always)

Include every section in this order. If a section is empty, leave a placeholder bullet — never omit the header. The last line of the body is the `Co-Authored-By` trailer with the model version powering the session.

````markdown
**Summary 📝**
-------

One sentence that tells a reader what this PR does and why.

**Before this 🐝**
-------

-

**What this PR does 🧑‍💻**
-------

- ✅ Change 1 — one line
- ✅ Change 2 — one line
- ✅ Change 3 — one line

**Testing 🧪**
-------

- [What you exercised by hand and what you saw]
- pr-review-toolkit was run; high-priority findings were fixed <!-- omit on simple PRs (see Workflow step 5) -->

**Revertable? ♻️**
-------

-

**Risk 🔥**
-------

-

**What to Watch 👀**
-------

Any `regression` or `should_not` item breached on two consecutive polls, or any `success` item unmet at window end → alert the user.

```yaml
watch:
  - id: orders-create-5xx
    kind: regression
    source: axiom
    query: "['vercel'] | where path == '/api/orders' and status >= 500 | count()"
    expect: value <= baseline * 2
    baseline: prior_7d
    window: 24h
    ref: src/app/api/orders/route.ts:41
    observed: { value: 3, at: 2026-10-10 }
```

**Relevant Links 🔗**
-------

- 💬 **Discussion**: [descriptive title](link)
- 🐛 **Issue / ticket**: [descriptive title](link)
- 📄 **Design doc**: [descriptive title](link)

Co-Authored-By: Claude <model version>
````

**Rules:** Summary: exactly one sentence. What this PR does: **3 bullets max**, one line each — less is more; the diff carries the detail. Testing: manual verification only — never mention unit tests, linters, type checks, or build commands, since CI gates all of them before merge. What to Watch: the yaml block is the only content besides the standing alert line; `watch: none` plus `reason:` when nothing qualifies (schema and rules in the reference). Links: descriptive text, never naked URLs. Formatting: emoji-after-titles, blank line after each header, no `---` separators, conversational bullets.

## Review comments

**Attribute:** prepend `**[CLAUDE]**` to every PR comment and review reply you write. Other agents use their own tag (`**[GEMINI]**`, `**[COPILOT]**`) — match `AGENTS.md`.

**Reply to every comment** (human or bot) with one of: **agree** (and fix or open follow-up), **disagree** (and explain), **defer** (link an issue). Silence reads as ignored. Use `mcp__github__add_reply_to_pull_request_comment`.

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

## Common mistakes

| Mistake                                                                                           | Fix                                                                                |
| ------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| Reached for `gh pr create` first                                                                  | Default to MCP `create_pull_request`                                               |
| Used naked URL in Links section                                                                   | Wrap in descriptive link text                                                      |
| Mentioned unit tests, linters, type checks, or builds in Testing                                  | Delete — CI gates these before merge                                               |
| Wrote more than 3 "What this PR does" bullets, or padded them with rationale                      | Cut to 3 one-line bullets                                                          |
| Summary ran to two sentences                                                                      | Cut to one                                                                         |
| What to Watch item with a `source` not declared in `AGENTS.md`, or a `ref` that isn't in the diff | Drop the item; if none remain, `watch: none` with a reason                         |
| `baseline: prior_7d` without `observed`                                                           | Run the query over the prior 7 days on main and record it, or set `baseline: none` |
| Opened the PR with an unreachable alert route                                                     | Stop at preflight; fix the wiring first                                            |
| Hard-coded `draft: true` regardless of project                                                    | Check the project's `CLAUDE.md` / `AGENTS.md` first                                |
| Skipped `pr-review-toolkit` run on a non-simple PR                                                | Run it and wait for user feedback (skip only on docs/tests-only or <500 LOC)       |
| Forgot to open PR in browser                                                                      | `gh pr view <N> --web` after creation                                              |
| Left a review comment unanswered                                                                  | Reply agree / disagree / defer to every comment                                    |
| Forgot the `Co-Authored-By` trailer                                                               | Last line of the body, with the current model version                              |
