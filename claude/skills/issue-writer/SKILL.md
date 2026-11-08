---
name: issue-writer
description: Use when creating, drafting, or rewriting an issue or ticket in GitHub Issues, Linear, or Jira — a bug report, feature request, follow-up, or task — or when the user asks to write, file, open, or clean up a ticket or issue ("write a ticket for this"). Not for wayfinder map or decision tickets, which keep wayfinder's shape.
---

# Writing an Issue

## Overview

Every issue has the same short shape: a problem, a proposal, and acceptance criteria someone can check. The project's own criteria come from its `AGENTS.md`. The same body goes to any tracker; only the create call differs.

## 1. Read the project's `## Issues` section

Look for an `Issues` heading, at any level, in the project's `AGENTS.md`. It may declare:

- **Tracker:** `github <owner/repo>`, `linear <team>`, or `jira <project key>`. With no section, use the git remote's GitHub repo.
- **Titles:** a format that replaces the default.
- **Agent validation:** how and where the agent checks a change before merge.
- **Other named criteria** (for example `Spans:` or `Axiom logging:`). Each one becomes an acceptance criterion.

## 2. Check main before drafting

Read the code the report touches on the default branch. If a merged PR already fixes some of it, tell the user and name the PR. Write the issue only for what's still wrong.

## 3. Draft the title and body

**Title:** `<Area>: <outcome>`, at most 70 characters. Use the project's `Titles:` format if it declares one.

**Body:**

```markdown
**Problem.** <1–3 sentences: what's wrong or missing, who sees it, and why now if that's known.>

**Proposal.**

- <≤ 5 bullets, one sentence each; code pointers as `path` or `path:line`>
- Open: <an unresolved choice, if any, as its own bullet>

**Acceptance criteria.**

- [ ] <2–5 task-specific items, each a page state, a command's output, or a test that fails when the fix is reverted>
- [ ] <Criterion name>: <what this change does about it> (one item per project criterion)
- [ ] Agent validation: <where the change runs> — <what the agent does and sees>

**Out of scope.**

- <≤ 3 bullets; omit the section when empty>

Links: <blocked by #n · related PRs · RFC · parent; omit when empty>
```

- **Body:** at most 250 words of prose. Code spans, URLs, and list or checkbox markers don't count.
- **Bug:** Problem may add up to 5 lines of steps to reproduce, quoting the reporter's words.
- **Report with more than one unrelated outcome** (for example, a bug plus a feature request): draft one issue per outcome, and tell the user you split it.
- **Open design question:** replace Proposal with **Options.**, up to 3 one-line bullets. The criteria are the decisions to make, plus "RFC merged".
- **Tracking issue** (a checklist of child issues): keep it a checklist, with no other sections.
- **Criterion that doesn't apply:** `- [ ] <Criterion name>: n/a, <reason>`. This format is the same in every project. Agent validation is n/a only when nothing runs differently (docs only, tooling only).

## 4. Self-check the draft, fix it, then show it

1. The title fits the format and is at most 70 characters.
2. Each section is within its limit, and the body is at most 250 words.
3. Every acceptance criterion is a `- [ ]` item a reviewer can check by looking, running, or reading a test. Rewrite vague items such as "works correctly" or "handles edge cases" into the observable case they mean.
4. Each criterion from the project's Issues section has an item.
5. The agent validation item names a place (a URL, a lane, or a service) and what is observed.
6. The Problem says what's wrong, and the criteria say how to check it's fixed. No other sentence says the same thing twice, and no section appears beyond the shape.

## 5. Get a yes, then create

- **New issue:** show the title and body, then wait for the user's explicit "yes, open it". Create it only after that yes. The user's yes covers that one issue, not any follow-ups.
- **Rewrite:** only when the user names the issue. Show a short before/after diff of the body, then update the issue on their yes.

Create and update commands for each tracker: [references/trackers.md](references/trackers.md).

## Common mistakes

| Mistake                                                    | Fix                                                             |
| ---------------------------------------------------------- | --------------------------------------------------------------- |
| Background paragraphs ahead of the Problem                 | Keep only the 1–3 sentences. Put the rest in Links or the PR    |
| Pasting code or a full investigation into the issue        | Give a `path:line` pointer instead                              |
| "Tests pass" given as the agent validation                 | Name the browser URL, lane, or service, and what the agent sees |
| Dropping a project criterion because it seems not to apply | Keep the item and write `n/a, <reason>`                         |
| Creating the issue right after drafting it                 | Wait for "yes, open it"                                         |
