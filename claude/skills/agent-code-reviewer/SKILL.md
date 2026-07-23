---
name: agent-code-reviewer
description: Use to request a SECOND-OPINION review of code, PRs, or architecture from a different model (Gemini or Codex) via `cli/agent_code_reviewer.py`. Reviewer provides feedback only — never writes code. Do NOT use when the user wants Codex (or another model) to **implement, fix, refactor, or write** code; that is the `codex:rescue` skill's job (if the OpenAI Codex plugin is installed).
---

# Agent Code Reviewer

## Overview

`cli/agent_code_reviewer.py` is a Python CLI that lets Claude get a second opinion from Gemini (default) or Codex / GPT. The script handles all the deterministic protocol mechanics: auth, request shape, response parsing, conversation history, `gh` integration for posting inline PR comments. **This skill encodes the judgment layer**: when to invoke it, which provider to pick, how to read the output, when to push back.

Flag enumeration, env-var setup, and exit codes live in the script's `--help` and module docstring — read those once at the source; do not paraphrase them here.

## Red Flags — STOP

| Rationalization                                          | Reality                                                                                                                                                                                                                                                           |
| -------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| "User said 'use Codex' — invoke this skill"              | If they want Codex to **review** code, use this skill. If they want Codex to **write or fix** code, use the `codex:rescue` skill from the OpenAI Codex plugin (if installed); otherwise tell the user the request is for delegation, which this skill doesn't do. |
| "Every PR deserves a second opinion before merge"        | Token cost is real. Reserve second opinions for PRs that touch auth, money, migrations, or new subsystems. Trivial chores don't earn a review.                                                                                                                    |
| "Reviewer disagreed — apply their fix"                   | Reviewers are wrong constantly. Treat their output as input, not instruction. Push back in-conversation when you have a stronger argument; don't silently capitulate.                                                                                             |
| "I'll skim the reviewer output and pick what looks good" | Edge-case flags and security/migration concerns deserve a deliberate accept/disagree/defer reply per comment, same as a human reviewer. Cherry-picking trains you to ignore the parts that matter.                                                                |

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

## Picking a provider

The judgment, not a flag table:

- **Gemini** (default): generally faster turnaround and cheaper, strong at line-level diff review. Default for routine `--pr` reviews and quick sanity passes.
- **Codex** (GPT-5.5): better at architecture-level critique on novel subsystems; stronger at spotting subtle invariants in tightly coupled modules. Reach for it when the diff is _small but conceptually load-bearing_ — e.g., a new lock-free data structure, a security boundary, a non-obvious algorithm.

`--lite` rationale:

- Use the lite (`flash-lite` / `gpt-5.4-mini`) variant for: diffs under ~200 lines, sanity passes on routine refactors, fast iteration loops where you'll run the reviewer multiple times.
- Don't use lite for: architecture review, security audits, anything where the model is the only second pair of eyes.

If you're unsure, default to Gemini full-model — the script's defaults match this.

## Reading reviewer output

Reviewers will produce a mix of: edge-case flags, style/idiom opinions, performance observations, and (occasionally) architecture rewrites. Weight them like this:

- **Edge-case flags**: take seriously. The whole reason for a second opinion is the cases you didn't think of. If the flag describes a real input that breaks the code, fix or defer with an issue link — don't dismiss.
- **Security / migration concerns**: take seriously, always. Even when wrong, they cost little to verify and the false-negative cost is catastrophic.
- **Performance observations**: investigate if they cite a specific hot path or complexity claim; ignore if they're hand-wavy ("this could be faster").
- **Style / idiom opinions**: advisory only. Apply if the rule matches the project's existing AGENTS.md / style; ignore otherwise.
- **Architecture rewrites**: never silently accept. Re-ground in the original spec and the question you actually asked. Often the reviewer didn't have the context for the constraint you'd already considered.

## Praise budget

Reviews exist to surface problems; praise is a rounding error on their value. The script's system prompts already encode this — hold the same line when you relay or summarize.

- **At most 2 sentences of praise per review, and only in the top-level summary.**
- **Never in per-line / inline comments.** Every inline comment must flag something needing attention; a line with nothing wrong gets no comment.
- **Praise is optional.** Omit it entirely when nothing stands out — never manufacture it to soften a harsh review.
- When you summarize reviewer output for the user, don't re-inflate what the prompt trimmed.

## Push-back protocol

Reviewers are confident-sounding but often wrong. When a critique is wrong:

- **Respond in-conversation**, don't capitulate. The script persists conversation history — your push-back becomes part of the next turn's context, and the reviewer often refines or retracts.
- **State your reasoning concretely** ("the constraint here is X, which makes Y impractical") rather than "I disagree."
- **Cite the spec** if you have one — reviewers are bad at remembering scope you established earlier.
- **If they're persistent and you're certain**, log the disagreement (PR comment, `MEMORY.md` entry) and move on. The next maintainer benefits from knowing why a "obvious" suggestion wasn't applied.

When _they're right_, fix the code and reply to the PR comment with `**[CLAUDE]** Agree — fixed in <commit>` (or equivalent attribution).

## Conversation history hygiene

- The script auto-persists per-provider history. Default is fine for most flows.
- Pass `--session <uuid>` when you start a new logical task to avoid stale context bleeding into a fresh question. Generate one UUID per Claude conversation and reuse it across calls within that conversation.
- Pass `--reset` if you suspect the history is poisoned (e.g., reviewer fixated on a non-issue, or you switched topics entirely mid-conversation).
- Long debugging sessions: bump `--ttl` higher (e.g., `--ttl 120`) so context survives a coffee break. Default 30 minutes is sized for tight feedback loops.

## After you've used the script

- If it ran `--pr <N>` mode, the reviewer's inline comments are already on the PR. Reply to each one with `**[CLAUDE]** agree / disagree / defer + reason`, same protocol as a human reviewer.
- If it was a one-off question, summarize the takeaways in your response to the user — don't dump the raw reviewer output unless asked.
- If the reviewer flagged something that turned out to be a real codebase pattern issue (not just a one-shot bug), consider whether it belongs in `AGENTS.md` as a new rule, or in `MEMORY.md` as a gotcha note.

## Setup gotchas

The script's `--help` covers the full env-var list and setup steps. The two non-obvious things worth flagging:

- **API keys live in your shell profile or `~/.claude/settings.json`.** A user without `GEMINI_API_KEY` (or `OPENAI_API_KEY` for Codex) will see a clear error from the script; tell them to set up the key per the script's docstring, do not try to work around it.
- **Gemini's free tier rate limits are too low for PR review.** A Tier-1 paid key is the practical minimum. If a user hits rate limits, escalating to paid is the fix, not retry-with-backoff.
