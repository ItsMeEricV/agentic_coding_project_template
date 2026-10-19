# Vertical slices for `--pr`

Read this only after a whole-diff pass has run and either its stderr listed focus areas or the script refused the diff (exit 3) with no roster entry that fits. The gate itself (same PR head, a nomination or a 150K+ token pass, at most three slices, exit 4 otherwise) is enforced by the script and documented in its docstring; this file covers the judgment of whether to use the slices it would allow.

## Why slices exist, and why the default is zero

Attention per line drops as the prompt grows. On a 190K-token PR, the races and off-by-one-attempt bugs that four small passes find will not all surface in one. On a 40K-token PR that loss does not exist, and a slice is just a second full review of code the whole pass already covered. One whole pass plus three slices costs more than the four layer passes it replaced, so a slice has to buy a finding the whole pass could not reach.

**Never slice by layer.** A reviewer that sees the router without the workflow that produces its events flags contracts the missing layer enforces, and every such finding is a false positive you then disprove on the PR. A slice is one invariant's router, workflow, and store together: `--only-path` naming those files, `--file` attaching the sibling interfaces they still depend on, and the invariant as the question.

## The justification line

Before each slice runs, write one line in the conversation: the invariant it checks, why the whole pass could not settle it, and which source below named it. If you cannot write that line, the slice does not run. Three such lines should read as three separate defenses, not one plan. Three is a ceiling you should rarely reach.

## Sources, in order of trust

Dedupe candidates by file overlap.

1. **Reviewer-nominated.** The whole pass may return `focus_areas`: invariants it could not settle from the diff alone, with the files a focused pass must see together. They appear under "Suggested focused passes" in the review body and, with per-file churn, in `/tmp/agent_reviewer_<owner>_<repo>_pr<N>_focus.json`. Read that file first. Nominating "the hard part is here" survives a long prompt far better than finding the bug in it, which is why this is the only source that clears the gate on its own. It still does not guarantee a slice: a nomination whose files the whole pass already judged cleanly, with the enforcing code in view, is a nomination to decline.
2. **Project-declared.** `ARCHITECTURE.md` lists invariants with the paths that enforce them; one whose paths this diff touches **and** the whole pass left a signal on is a candidate. `KNOWLEDGE.md`'s flagged ambiguities mark places the team itself is unsure. `AGENTS.md` rules are generic and never select a slice.
3. **Diff-derived.** From the focus file's `churn`: the most-changed files, and code changes with no matching test changes. A tie-breaker between candidates that already have a signal, never a reason on its own.
4. **Risk vocabulary.** Shared mutable state, retry and idempotency paths, authorization boundaries, migrations, money. This names what a signal tends to be about; it is not a checklist to slice through. An empty nomination list gets no slice from here.

## Running one

Phrase the invariant as something that can hold: the reviewer is told that "holds" and "unsettled" are complete answers. Use `--dry-run` to read the slice before any of it reaches the PR.

```bash
uv run cli/agent_code_reviewer.py --pr 67 \
  --only-path 'packages/core/session/' --only-path 'apps/dispatcher-core/src/workflows/' \
  --file packages/core/session/session-service.ts --file docs/rfcs/0009-session-workflow.md \
  --dry-run \
  "Check one invariant: a cancelled task always ends in abandonStepRun(cancelled), and no sandbox outlives its session."
```

A refusal (exit 4) is not a prompt to work around the gate. It means run the whole pass again or stop.
