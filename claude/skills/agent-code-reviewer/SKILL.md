---
name: agent-code-reviewer
description: Use to request a SECOND-OPINION review of code, PRs, or architecture from a different model (Gemini, Codex, or anything on OpenRouter) via `cli/agent_code_reviewer.py`. Reviewer provides feedback only — never writes code. Do NOT use when the user wants another model to **implement, fix, refactor, or write** code — this skill is review-only.
---

# Agent Code Reviewer

## Overview

`cli/agent_code_reviewer.py` is a Python CLI that lets Claude get a second opinion from another model. The script handles all the deterministic protocol mechanics: auth, request shape, response parsing, conversation history, `gh` integration for posting inline PR comments. **This skill encodes the judgment layer**: when to invoke it, which model to pick, how to read the output, when to push back.

The available models are data, not code — they live in the roster at `cli/agent_reviewer.toml`, keyed by a short slug you pass to `--model`. **Run `uv run cli/agent_code_reviewer.py --list` before picking one**: rosters differ per project, and the listing shows which entries actually have their API key set. Never assume a key exists because it existed in another repo.

Flag enumeration, env-var setup, and exit codes live in the script's `--help` and module docstring — read those once at the source; do not paraphrase them here.

## Red Flags — STOP

| Rationalization                                               | Reality                                                                                                                                                                                                                                                                                                                                                            |
| ------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| "User named a model — invoke this skill"                      | Depends on the verb. If they want that model to **review** code, use this skill. If they want it to **write, fix, or refactor** code, that is delegation, which this skill never does — hand off to whatever delegation skill the harness provides for that model (e.g. `codex:rescue` from the OpenAI Codex plugin), or tell the user no such skill is installed. |
| "Every PR deserves a second opinion before merge"             | Token cost is real. Reserve second opinions for PRs that touch auth, money, migrations, or new subsystems. Trivial chores don't earn a review.                                                                                                                                                                                                                     |
| "Reviewer disagreed — apply their fix"                        | Reviewers are wrong constantly. Treat their output as input, not instruction. Push back in-conversation when you have a stronger argument; don't silently capitulate.                                                                                                                                                                                              |
| "The diff is huge — I'll review it one package at a time"     | Slicing by layer hands the reviewer a router with no workflow, or a workflow with no store, so it flags contracts the other layer enforces. Send it whole; the script sizes the diff to the model's window and refuses what won't fit. Slice by vertical only after a refusal — see [Sizing and context](#sizing-and-context-for---pr).                            |
| "The reviewer read the spec literally, but I chose otherwise" | That is not a Disagree. If the reviewer's reading matches the approved text and you deliberately deviated, the user decides — reply **Escalate**, not Disagree.                                                                                                                                                                                                    |
| "I'll skim the reviewer output and pick what looks good"      | Edge-case flags and security/migration concerns deserve a deliberate accept/disagree/defer reply per comment, same as a human reviewer. Cherry-picking trains you to ignore the parts that matter.                                                                                                                                                                 |

## When to invoke

Use the script when one of these is true:

- **PR is about to be marked ready or merged**, AND it touches: authentication, payments, database migrations, a new subsystem, public APIs, or anything you'd want a senior IC to eyeball before shipping.
- **You're stuck debugging for >2 cycles** on the same root-cause hypothesis. A fresh model often spots the wrong assumption.
- **You wrote a non-trivial design or architecture doc** and want it stress-tested before locking it in.
- **The user explicitly asks for a second opinion / external review.**

Do NOT use it for:

- Chores (lint fixes, comment cleanup, dependency bumps with no behavior change).
- One-line bug fixes with obvious correctness.
- Generic "is this code OK?" without a specific question — reviewers without a sharp prompt return generic noise.

## Picking a model

Read the roster first (`--list`), then apply judgment. The keys below are the shipped defaults; a project may have renamed or replaced them.

- **A deep model from a different family than the code's author.** The entire value of a second opinion is a different prior. Reviewing Claude-written code with the roster's Codex, Gemini, or Grok entry beats any same-family pairing — a roster may also carry Claude entries (`opus`, `haiku`), which are the weakest choice on your own diffs and should be reserved for when the user explicitly wants Claude's read.
- **Frontier / "pro" tier for anything load-bearing**: architecture review, security boundaries, migrations, novel subsystems. This is the common case — superficial reviews are rarely worth the tokens.
- **A lite tier** (e.g. `gemini-lite`) only for: diffs under ~200 lines, sanity passes on routine refactors, fast iteration loops where you'll run the reviewer several times. Never for architecture review, security audits, or when the model is the only second pair of eyes.
- **Reach past the default** when the diff is _small but conceptually load-bearing_ — a lock-free data structure, a security boundary, a non-obvious algorithm. A second, differently-familied opinion on the same diff is cheap insurance there.

- **Check the CONTEXT column for a big PR.** `--list` shows each entry's window. If the script refuses the diff (exit 3), its message names the entries that would take it — pick one of those rather than slicing.

If you're unsure, omit `--model` — the roster's `default` is set to the deep model the project trusts most.

## Adding a model to the roster

Never edit `cli/agent_reviewer.toml` unless the user asked. Adding an entry commits a model choice to the repo for every future run.

When they do ask ("add GPT Astra to the roster"), the only hard part is the provider's exact `id`. **Never guess a slug from a marketing name** — resolve it:

```bash
uv run cli/agent_code_reviewer.py --find-model astra
```

That searches OpenRouter's catalog (public, no API key) and prints each match's id, context window, per-million price, and whether it is an alias or a batch variant. Adding the entry itself never needs a Python change — the roster is data, and the three `access_method` adapters already cover every model these providers host.

Pick from what it returns:

- **Take the pinned id, not a floating alias** — the flag annotates aliases `alias -> <target>` and sorts them last. An alias silently changes model under a roster entry whose `key` and `name` still claim the old one.
- **Skip `:batch` variants.** Half price, but queued rather than interactive — wrong shape for a review loop you're waiting on.
- Set `tag` when the family already has one in the roster (the OpenAI/Codex entries share `CODEX`); otherwise it defaults to the key upper-cased and becomes a public label on PR comments.
- Confirm with `--list`, which resolves the roster and shows whether that entry's API key is set.

A model reachable only through a direct provider API (a preview id OpenRouter has not listed) won't appear. Get that id from the provider's own model list and set `access_method` to `gemini_api` or `openai_api` accordingly.

## Sizing and context for `--pr`

One pass over the whole diff is the default. The script sizes the diff to the entry's `context_window` and refuses one that does not fit (exit 3) instead of truncating it. A refusal names the roster entries that would take the diff; switch to one of those first.

Slice only when no entry takes it whole, and slice **by vertical, never by layer**: one invariant's router, workflow, and store go in the same pass, with `--ignore-path` dropping the rest. A reviewer that sees the router without the workflow that produces its events, or the workflow without the service that ends its rows, flags contracts the missing layer enforces — every such finding is a false positive you then have to disprove on the PR.

Give the reviewer the rationale, not a rule list. A paragraph of "binding rules" in the prompt turns the model into a linter that tags every deliberate deviation HIGH. Attach the design doc or decision log instead, with `--file` (repeatable; it rides along as read-only context the reviewer judges the diff against but does not comment on):

```bash
uv run cli/agent_code_reviewer.py --pr 67 --file docs/rfcs/0009-session-workflow.md "Focus on cancellation and retry paths"
```

When a slice is unavoidable, attach the sibling layer's interface file the same way so the contract is in the prompt even though its implementation is not.

## Reading reviewer output

Reviewers will produce a mix of: edge-case flags, style/idiom opinions, performance observations, and (occasionally) architecture rewrites. Weight them like this:

- **Edge-case flags**: take seriously. The whole reason for a second opinion is the cases you didn't think of. If the flag describes a real input that breaks the code, fix or defer with an issue link — don't dismiss.
- **Security / migration concerns**: take seriously, always. Even when wrong, they cost little to verify and the false-negative cost is catastrophic.
- **Performance observations**: investigate if they cite a specific hot path or complexity claim; ignore if they're hand-wavy ("this could be faster").
- **Style / idiom opinions**: advisory only. Apply if the rule matches the project's existing AGENTS.md / style; ignore otherwise.
- **Architecture rewrites**: never silently accept. Re-ground in the original spec and the question you actually asked. Often the reviewer didn't have the context for the constraint you'd already considered.
- **Findings about a contract enforced elsewhere** ("stale events can arrive", "cancel skips cleanup"): check whether the enforcing code was in the diff the reviewer saw. If it was not, verify the invariant in that code before replying, cite the file in the reply, and attach it with `--file` on the next run.

## Praise budget

Reviews exist to surface problems; praise is a rounding error on their value. The script's system prompts already encode this — hold the same line when you relay or summarize.

- **At most 2 sentences of praise per review, and only in the top-level summary.**
- **Never in per-line / inline comments.** Every inline comment must flag something needing attention; a line with nothing wrong gets no comment.
- **Praise is optional.** Omit it entirely when nothing stands out — never manufacture it to soften a harsh review.
- **Never reply to praise.** No "thanks", no acknowledgement, no PR comment response. Praise carries no action item, so a reply just starts a back-and-forth that costs tokens and buries the real comments. Skip it silently and move to the next item.
- When you summarize reviewer output for the user, don't re-inflate what the prompt trimmed.

## Push-back protocol

Reviewers are confident-sounding but often wrong. When a critique is wrong:

- **In conversation mode, respond in-conversation**, don't capitulate. The script persists history — your push-back becomes part of the next turn's context, and the reviewer often refines or retracts.
- **In `--pr` mode there is no second turn.** Each run is single-shot and the reviewer never sees your replies, so a PR reply is a record for the user and the next maintainer, not an argument the reviewer can retract. Hold it to the same standard: a verifiable claim with a file cited, not an assertion.
- **State your reasoning concretely** ("the constraint here is X, which makes Y impractical") rather than "I disagree."
- **Cite the spec** if you have one — reviewers are bad at remembering scope you established earlier.
- **Separate "wrong" from "overruled."** When the reviewer's reading matches the approved spec and you deliberately deviated, you do not get to disagree; that is the user's call. Reply **Escalate** and name the commits that would revert the deviation.
- **If they're persistent and you're certain**, log the disagreement (PR comment, `MEMORY.md` entry) and move on. The next maintainer benefits from knowing why a "obvious" suggestion wasn't applied.

When _they're right_, fix the code and reply to the PR comment with `**[CLAUDE]** Agree — fixed in <commit>` (or equivalent attribution).

## Conversation history hygiene

- The script auto-persists history per roster entry (`/tmp/agent_reviewer_<key>.json`), so switching `--model` starts a clean thread rather than inheriting the other model's context. Default is fine for most flows.
- Pass `--session <uuid>` when you start a new logical task to avoid stale context bleeding into a fresh question. Generate one UUID per Claude conversation and reuse it across calls within that conversation.
- Pass `--reset` if you suspect the history is poisoned (e.g., reviewer fixated on a non-issue, or you switched topics entirely mid-conversation).
- Long debugging sessions: bump `--ttl` higher (e.g., `--ttl 120`) so context survives a coffee break. Default 30 minutes is sized for tight feedback loops.

## After you've used the script

- If it ran `--pr <N>` mode, the reviewer's inline comments are already on the PR. Reply to each _actionable_ one with `**[CLAUDE]** Agree / Disagree / Defer / Escalate + reason`, same protocol as a human reviewer. **Agree** fixes and names the commit. **Disagree** cites the code or spec that refutes the finding. **Defer** names the ticket or build that will take it. **Escalate** is for a correct reading of the spec that you deliberately deviated from — state the trade-off and the reverting commits, and let the user rule. Leave praise unanswered — see [Praise budget](#praise-budget).
- If it was a one-off question, summarize the takeaways in your response to the user — don't dump the raw reviewer output unless asked.
- If the reviewer flagged something that turned out to be a real codebase pattern issue (not just a one-shot bug), consider whether it belongs in `AGENTS.md` as a new rule, or in `MEMORY.md` as a gotcha note.

## Setup gotchas

The script's `--help` covers the full env-var list and setup steps. The two non-obvious things worth flagging:

- **Run it with `uv run`.** The script declares its dependencies in a PEP 723 header, so `uv run cli/agent_code_reviewer.py …` resolves them per-run with no venv to manage. Bare `python3` works for every access method except `openrouter`, whose SDK import will fail.
- **API keys live in your shell profile or `~/.claude/settings.json`**, one per access method: `GEMINI_API_KEY`, `OPENAI_API_KEY`, `OPENROUTER_API_KEY`. `--list` shows which are set. A user missing one sees a clear error naming the var; tell them to set it, do not try to work around it.
- **Exit code 2 means the roster is wrong** (bad TOML, unknown `--model` key), not that the API failed. Fix the invocation or the config — do not retry.
- **Exit code 3 means the diff does not fit the model's window.** The message names roster entries that would take it. Switch model, or slice by vertical — see [Sizing and context](#sizing-and-context-for---pr). Never retry the same entry.
- **Gemini's free tier rate limits are too low for PR review.** A Tier-1 paid key is the practical minimum. If a user hits rate limits, escalating to paid is the fix, not retry-with-backoff.
