# A consistent issue shape: the `issue-writer` skill

Status: proposal, awaiting the user's approval. Nothing is built yet.

Issues in werkshop and fitness_tracker share no shape. Headings vary (`Problem.`, `Summary 📝`, `What we want`, `Done when`), acceptance criteria are sometimes missing (werkshop #438, fitness_tracker #632, #610), and bodies run long: werkshop #478, #479, #473 are 340–490 words; fitness_tracker #623 and #622 are 710–920. Neither repo asks whether a change needs telemetry or a pre-merge check in the running app.

## Decisions

**A skill, not a script.** Writing the body is judgment work: what the problem is, what's out of scope, which criteria can be checked. A script can't do that. The only tracker-specific step is one create call, and agents already have a tool for each tracker (`gh`, Linear's MCP, Atlassian's MCP). A script would need its own login for each tracker, which means new tokens or env vars. The checks in "Self-check" are mechanical enough that the skill can run them. If drafts drift anyway, they can become a small lint script later.

**One generic skill, with each project's criteria in its `AGENTS.md`.** This copies the `pull-request-creator` split. The skill holds the shape, the limits, the self-check, and the shared criterion. Each project's `AGENTS.md` gets an `## Issues` section naming its tracker, how to run the agent validation, and its own criteria. A per-project copy of the skill was considered and rejected: copies drift, and a fix to the shape would have to be made in every repo. A project that needs nothing extra declares only its tracker.

**The skill drafts. A person says "yes, open it".** The skill shows the title and body, then creates the issue only after the user's explicit yes, as the global rules require.

**Rewrites happen only on request, after a before/after.** If the user asks for issue N to be rewritten, the skill shows a short before/after diff of the body and updates the issue on the user's yes. It never reformats issues on its own.

**One title format: `<Area>: <outcome>`, at most 70 characters.** A project can override it with a `Titles:` line in its `## Issues` section.

## The shape

```markdown
<Area>: <outcome>

**Problem.** 1–3 sentences: what's wrong or missing, who sees it, why now.

**Proposal.** ≤ 5 one-line bullets. Code pointers as `path` or `path:line`, no pasted code.
(For an open design question: **Options.** ≤ 3 one-line bullets instead.)

**Acceptance criteria.**

- [ ] 2–5 task-specific items, each something a reviewer can check
- [ ] <one item per project criterion, or "<criterion>: n/a, <reason>">
- [ ] Agent validation: <where and what the agent exercises before merge>

**Out of scope.** ≤ 3 bullets. Optional.

Links: blocked by #n · RFC · parent. One line, optional.
```

- **Body cap: 250 words** without code spans. Each section has its own cap, shown above.
- **Bugs:** Problem may add ≤ 5 lines of steps to reproduce, quoting the user's report if there is one.
- **Design issues** (like #438): the acceptance criteria are the decisions an RFC has to make, plus "RFC merged".
- **Tracking issues** (like #469): exempt. They stay a checklist of child issues.

## The criterion every issue gets: agent validation before merge

Before merge, the agent exercises the change where it really runs: a browser on the local stack, the preview lane, or the real service. It records what it saw in the PR's Testing section. Passing tests don't count. The item names where the check happens and what is observed. A change with no runtime surface (docs only, tooling only) writes `Agent validation: n/a, <reason>`, and the user can reject that when reviewing the issue. The skill always adds this item. Each project says how to run the check.

## Project sections (worked examples)

werkshop `AGENTS.md`:

```markdown
## Issues

- **Tracker:** github `ItsMeEricV/werkshop`.
- **Agent validation:** on the local stack (`pnpm bootstrap:dev`), drive the change through web
  in a browser (`chrome-werkshop` MCP) or start a real session; a lane change is checked on preview.
- **Spans:** a new step, workflow path, external call, or edge says which spans and attributes it
  adds from RFC 0022's vocabulary (§3), through the telemetry door, or `Spans: n/a, <reason>`.
```

fitness_tracker `AGENTS.md`:

```markdown
## Issues

- **Tracker:** github `ItsMeEricV/fitness_tracker`.
- **Agent validation:** in a browser on `movata.local:$WEB_PORT` with the dev login
  (see "Dev browser login"), via `cmux:browser`; subdomain changes also on `<slug>.movata.local`.
- **Axiom logging:** a new server path or failure mode logs through `@/lib/logger` with
  fields queryable in `palaestra-logs` (units in latency names), or `Axiom logging: n/a, <reason>`.
```

## Trackers: one body, a different create step

| Tracker | Create step                                                                            | Body format                                                                                                                                                                         |
| ------- | -------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| GitHub  | `gh issue create -R <slug> --title … --body-file -`                                    | Markdown; `- [ ]` renders as a task list                                                                                                                                            |
| Linear  | Linear MCP `save_issue` (team, title, description)                                     | Markdown description ([Linear docs](https://linear.app/docs/mcp))                                                                                                                   |
| Jira    | Atlassian MCP `createJiraIssue` (project, issueType, summary, description as Markdown) | REST v3 needs ADF ([Jira REST v3](https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issues/)), so use the MCP; `- [ ]` may arrive as plain text, still readable |

The tracker comes from the project's `## Issues` section. With no section, the skill uses the git remote's GitHub repo.

## Before and after: werkshop #478

Before: [#478](https://github.com/ItsMeEricV/werkshop/issues/478), 339 words. A problem section with three sub-bullets, three numbered proposals, and four criteria. It has no telemetry item and no check in the running app.

After, 216 words:

```markdown
Repository access: one name, and list the repos werkshop can see

**Problem.** Connecting GitHub has four names across the UI, docs, and GitHub ("Connect GitHub",
"install the App", …), and a connected account never shows which repositories werkshop can see.
Users can't tell whether they've done the step, which blocks the fitness_tracker pilot.

**Proposal.**

- Call it "repository access" everywhere (UI, `docs/`, KNOWLEDGE.md); one line names the lane's App.
- The connected panel (`apps/web/src/ui/install-github-app-panel.tsx`) lists each repository with
  its workshop count, config errors, and a "Change repositories on GitHub" link.
- Refresh on the install callback and on `installation_repositories` webhooks.

**Acceptance criteria.**

- [ ] Workshops page and tenant settings list the account's repositories, counts, and change link.
- [ ] Tests cover not connected, pending org approval, connected (including zero repos), suspended.
- [ ] `rg -i "install (the|werkshop|our) (github )?app" apps/web docs` finds only the explainer and the glossary alias.
- [ ] Spans: the `installation_repositories` refresh is traced per RFC 0022, or the PR says why not.
- [ ] Agent validation: on the local stack, connect a test account in the browser, change its
      repositories on GitHub, and see the panel update.

**Out of scope.** A per-lane App display name through a new env var (ask the user first).

Links: blocks #469
```

## Self-check (the skill runs this on its own draft before showing it)

1. The title follows the format (the default or the project's override) and is ≤ 70 characters. Every section is within its cap, and the body is ≤ 250 words.
2. Every acceptance criterion is a `- [ ]` item that names something observable: a page state, a command's output, a test that fails when the fix is reverted. Items like "works correctly", "handles edge cases", or "is robust" fail the check.
3. Each criterion from the project's `## Issues` section has an item or an `n/a, <reason>`.
4. The agent validation item names a place (a URL, a lane, or a service) and what is observed.
5. No filler: no "This issue…", no repeating the title, no "comprehensive / seamless / leverage / ensure that", and no headings beyond the shape's.

Any failure means the skill fixes the draft before showing it.

## What gets built after approval

- `claude/skills/issue-writer/SKILL.md` (shape, self-check, flow) and `references/trackers.md`.
- An `## Issues` placeholder in this template's `AGENTS.md`, next to What to Watch.
- The two project sections above, one PR in each repo.
