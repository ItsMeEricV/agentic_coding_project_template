---
name: agent-code-reviewer
description: Use to request a SECOND-OPINION review of code, PRs, or architecture from a different model (Gemini, Codex, or anything on OpenRouter) via `cli/agent_code_reviewer.py`. Reviewer provides feedback only — never writes code. Do NOT use when the user wants another model to **implement, fix, refactor, or write** code — this skill is review-only.
---

# Agent Code Reviewer

`cli/agent_code_reviewer.py` gets a second opinion on code, a PR, or a design from a model in a different family. The script owns the mechanics: auth, request shape, diff sizing, inline PR comments, the slice gate. Its `--help` and module docstring list every flag, env var, and exit code — read them there, do not paraphrase them here. This skill is the judgment layer: whether a review earns its cost, which model, how to weigh what comes back.

## When to invoke

Yes, when one holds:

- A PR is about to be marked ready or merged **and** touches auth, money, migrations, public APIs, or a new subsystem.
- You are stuck for more than two debugging cycles on the same root-cause hypothesis. A different prior spots the wrong assumption.
- You wrote a non-trivial design doc and want it stress-tested before locking it in.
- The user asks for a second opinion.

No, when:

- Chores, lint, dependency bumps with no behavior change, one-line fixes with obvious correctness. Token cost is real; a trivial diff does not earn a review.
- You have no sharp question. A reviewer without one returns generic noise.
- The user wants another model to **write, fix, or refactor** code. That is delegation, not review — hand off to the harness's delegation skill for that model (e.g. `codex:rescue`) or say none is installed.

## Picking a model

Omit `--model` by default. The roster's `default` is the deep model from a different family than the code's author, which is the whole value of a second opinion. Run `--list` only when you intend to deviate or the script reports a missing key; it is not a required preamble.

Deviate when:

- **Diff under ~200 lines and routine** → the lite tier (e.g. `gemini-lite`). Never for architecture, security, or when it is the only second pair of eyes.
- **Exit 3 (diff does not fit)** → the message names the roster entries that would take it. Pick one. Slicing is for risk, never for size.
- **User explicitly wants Claude's read** → `opus` / `haiku`. On Claude-authored diffs they are the weakest choice, so only on request.
- **The roster itself needs editing** (add, bump, check versions) → read `references/roster-maintenance.md`. Never edit `cli/agent_reviewer.toml` unprompted.

## Running it

```bash
uv run cli/agent_code_reviewer.py --pr 67 --file docs/rfcs/0009-session-workflow.md "Focus on cancellation and retry paths"
uv run cli/agent_code_reviewer.py --file src/lock.ts "Is the CAS loop safe under contention?"
```

- **`--pr` sends the whole diff in one pass, always.** It is the only pass that judges cross-layer contracts correctly.
- **Give rationale, not rules.** Attach the RFC, decision log, or the sibling layer's interface with `--file` (repeatable, read-only context). A paragraph of "binding rules" turns the reviewer into a linter that tags every deliberate deviation HIGH.
- **`--dry-run` the first time a roster entry reviews a PR**, so a malformed reply does not land on the PR as a raw-text summary.
- **A `--> Catalog check` report on stderr is news for the user, not a failure.** The review still ran. Put the report verbatim at the top of what you return, so it survives every agent that relays it; the user decides, per `references/roster-maintenance.md`. Never edit the roster or pass `--skip-version-check` on your own.
- **Slices default to zero.** Only when the whole pass's stderr reports focus areas, or exit 3 says no entry fits, read `references/vertical-slices.md`. Exit 4 means the pass did not earn the slice — run the whole pass again or stop; never work around the gate.
- **Conversation mode:** one `--session <uuid>` per Claude conversation; `--reset` when the reviewer fixates on a non-issue; a higher `--ttl` for long debugging sessions.

## Reading the output

Reviewers sound confident and are often wrong. Their output is input, not instruction.

- **Edge cases, security, migrations:** verify every one. Even a wrong flag is cheap to check and the false-negative cost is not. Fix, or defer with a link.
- **Performance:** investigate a named hot path or complexity claim; ignore "this could be faster".
- **Style:** advisory. Apply only when it matches the project's `AGENTS.md`.
- **Architecture rewrites:** re-ground in the spec and the question you asked. The reviewer usually lacks the constraint you already weighed.
- **A contract enforced elsewhere** ("stale events can arrive", "cancel skips cleanup"): check whether the enforcing code was in the diff it saw. If not, verify it there, cite the file in your reply, and attach it with `--file` next run.
- **Praise:** the script already caps it. Never reply to it, and do not re-inflate it when you summarize.

## Replying

PR mode is single-shot: the reviewer never sees your reply, so it is a record for the user and the next maintainer. Hold it to a verifiable claim with a file cited. Reply to each actionable comment as `**[CLAUDE]** <verb> — <reason>`:

- **Agree** — fixed in `<commit>`.
- **Disagree** — cite the code or spec that refutes the finding. "The constraint is X, which makes Y impractical", never bare "I disagree".
- **Defer** — the ticket or build that takes it.
- **Escalate** — the reviewer read the approved spec correctly and you deliberately deviated. That is the user's call, not a Disagree: state the trade-off and the commits that would revert it.

In conversation mode push back in-thread; history persists and the reviewer often refines or retracts. For a one-off question, summarize the takeaways rather than dumping raw output. A finding that exposes a codebase-wide pattern may belong in `AGENTS.md` as a rule or `MEMORY.md` as a gotcha.

## Gotchas `--help` does not cover

- **`uv run`, not `python3`.** Dependencies ride in a PEP 723 header; the `openrouter` adapter's import fails bare.
- **Gemini's free tier is too slow for PR review.** A Tier-1 paid key is the floor. Rate-limit errors mean upgrade, not retry.
- **Exit 2 is your invocation or the roster, not the API.** Fix it; do not retry.
