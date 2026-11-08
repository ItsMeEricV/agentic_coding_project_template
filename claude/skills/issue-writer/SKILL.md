---
name: issue-writer
description: Use when creating, drafting, or rewriting an issue or ticket in GitHub Issues, Linear, or Jira — a bug report, feature request, follow-up, or task — or when the user asks to write, file, open, or clean up a ticket or issue ("write a ticket for this"). Not for wayfinder map or decision tickets, which keep wayfinder's shape.
---

# Writing an Issue

Every issue has the same short shape: a problem, a proposal, and acceptance criteria someone can check. The shape keeps issues short enough to read, and it makes "done" something a reviewer can check rather than argue about.

## 1. Read the project's Issues section

Find the `Issues` heading in the project's `AGENTS.md`. It can declare:

- the tracker (`github <owner/repo>`, `linear <team>`, `jira <key>`; the default is the git remote's GitHub repo);
- a `Titles:` format;
- how agent validation is done;
- named criteria such as `Spans:` or `Axiom logging:`. Each one becomes an acceptance criterion.

## 2. Check the default branch

Read the code the report touches. If a merged PR already fixes some of it, tell the user and name the PR. Write the issue only for what's still wrong.

## 3. Draft

**Title:** `<Area>: <outcome>`, at most 70 characters, unless the project declares its own format.

**Body:** at most 250 words of prose. Code spans, URLs, and list markers don't count.

```markdown
**Problem.** <1–3 sentences: what's wrong or missing, who sees it, and why now if that's known.>

**Proposal.**

- <≤ 5 bullets, one sentence each; code pointers as `path:line`, never pasted code>
- Open: <an unresolved choice, if any>

**Acceptance criteria.**

- [ ] <2–5 items, each a page state, a command's output, or a test that fails when the fix is reverted>
- [ ] <Project criterion>: <what this change does about it>, or `n/a, <reason>`
- [ ] Agent validation: <URL, lane, or service> — <what the agent does and sees>

**Out of scope.**

- <≤ 3 bullets; omit when empty>

Links: <blocked by #n · related PRs · RFC · parent; omit when empty>
```

Agent validation is on every issue. Before merge, the agent runs the change where it really runs, not just in tests. It is n/a only when nothing runs differently (docs only, tooling only).

Bugs, reports that mix unrelated outcomes, open design questions, and tracking issues each need adjustments; see [references/shapes.md](references/shapes.md), which also has a worked example.

## 4. Self-check, fix, then show

1. The title fits its format and limit, and each section is within its limit.
2. Count the body's prose words. If there are more than 250, cut the Problem down to its 1–3 sentences first, then trim the Proposal. Readers skip long issues, so the limit is what keeps them read.
3. Every criterion is a `- [ ]` item a reviewer can check by looking, running, or reading a test. A vague item ("works correctly", "handles edge cases") gets rewritten as the observable case it means.
4. Every project criterion and the agent validation item are present. The agent validation item names a place and what is observed there.
5. Nothing is said twice, and no section appears beyond the shape.

## 5. Get a yes, then create

- **New issue:** show the title and body. Create it only after the user's explicit "yes, open it". A yes covers that one issue, not any follow-ups.
- **Rewrite:** only for an issue the user names. Show a short before/after diff, then update the issue on their yes.

Create and update commands for each tracker: [references/trackers.md](references/trackers.md).
