---
name: deep-discuss
description: Interview the user relentlessly about a plan or design until reaching shared understanding, resolving each branch of the decision tree. Stress-tests the plan against the project's documented language (KNOWLEDGE.md) and recorded decisions (RFCs), updating both inline as decisions firm up. Use when the user wants to stress-test a plan, get grilled on their design, or mentions "deep discussion".
---

## What to do

Interview me relentlessly about every aspect of this plan until we reach a shared understanding. Walk down each branch of the design tree, resolving dependencies between decisions one-by-one. For each question, provide your recommended answer.

Ask the questions one at a time. Do not be overly verbose.

If a question can be answered by exploring the codebase, explore the codebase instead.

## Ground the discussion in existing documentation

While exploring the codebase, also pull in whatever is already written down so the discussion builds on it rather than relabeling it.

### Where the docs live

Most repos hold a single body of knowledge:

```
/
├── KNOWLEDGE.md
├── docs/
│   └── rfc/
│       ├── 0001-event-sourced-orders.md
│       └── 0002-postgres-for-write-model.md
└── src/
```

If a `KNOWLEDGE-MAP.md` sits at the repo root, the project spans multiple areas of knowledge. The map says where each one lives and how they relate:

```
/
├── KNOWLEDGE-MAP.md
├── docs/
│   └── rfc/                          ← system-wide decisions
├── src/
│   ├── ordering/
│   │   ├── KNOWLEDGE.md
│   │   └── docs/rfc/                 ← area-specific decisions
│   └── billing/
│       ├── KNOWLEDGE.md
│       └── docs/rfc/
```

Create these files lazily — only once you actually have something to write. No `KNOWLEDGE.md`? Create it the moment the first term gets pinned down. No `docs/rfc/`? Create it when the first RFC is warranted.

When a `KNOWLEDGE-MAP.md` exists, work out which area the current topic belongs to before editing anything. If it is ambiguous, ask.

## During the session

### Hold the user to their own glossary

When the user uses a term that contradicts a definition already in `KNOWLEDGE.md`, stop and name the conflict: "KNOWLEDGE.md defines 'cancellation' as X, but you're using it to mean Y — which one is correct?" Either the user is being loose, or the glossary is stale; resolve which.

### Sharpen fuzzy language

When the user reaches for a vague or overloaded word, push for a precise canonical term. "You said 'account' — do you mean the Customer or the User? Those are not the same thing, and the plan reads differently depending on which."

### Pressure-test with concrete scenarios

When domain relationships come up, invent specific scenarios that probe the edges. Force the user to be exact about where one concept stops and the next begins.

### Check claims against the code

When the user states how something works, verify it against the actual code. If they disagree, surface it: "The code cancels whole Orders, but you just described partial cancellation — which is the real behavior?"

### Update KNOWLEDGE.md inline

The moment a term is resolved, write it into `KNOWLEDGE.md`. Do not batch these — capture each one as it lands. Follow [KNOWLEDGE-FORMAT.md](./KNOWLEDGE-FORMAT.md).

`KNOWLEDGE.md` is a glossary and shared-understanding document — nothing else. Keep implementation details, specs, and scratch notes out of it.

### Offer RFCs sparingly

Only offer to write an RFC when all three are true:

1. **Hard to reverse** — changing your mind later carries a real cost
2. **Surprising without context** — a future reader will ask "why was it done this way?"
3. **The outcome of a genuine trade-off** — there were real alternatives and one was chosen for specific reasons

If any one is missing, skip the RFC. Follow [RFC-FORMAT.md](./RFC-FORMAT.md).
