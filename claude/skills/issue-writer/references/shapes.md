# Adjusting the shape, and a worked example

## Adjustments

- **Bug:** after the Problem sentences, add up to 5 lines of steps to reproduce, in the reporter's own words.
- **Report with more than one unrelated outcome** (for example, a bug plus a feature request): draft one issue per outcome, and tell the user you split it. Each issue gets its own criteria and its own check.
- **Open design question:** replace Proposal with **Options.**, at most 3 one-line bullets. The acceptance criteria become the decisions an RFC has to make, plus "RFC merged".
- **Tracking issue** (a parent that lists child issues): keep it a checklist of the child issues, with none of the other sections.
- **Criterion that doesn't apply:** keep the item and write `<Criterion>: n/a, <reason>`. The format is the same in every project, so a reviewer can tell at a glance that the criterion was weighed and set aside.

## Worked example (werkshop #478, rewritten from 339 words)

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
- [ ] Spans: the `installation_repositories` refresh is traced per RFC 0022.
- [ ] Agent validation: local stack, `https://local.werkshop.dev` — connect a test account, change its
      repositories on GitHub, and see the panel update.

**Out of scope.**

- A per-lane App display name through a new env var (ask the user first).

Links: blocks #469
```
