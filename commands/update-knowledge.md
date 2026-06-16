---
description: Reconcile KNOWLEDGE.md with the domain terms discussed this session
---

# Reconcile KNOWLEDGE.md

You are reconciling the project's domain glossary against what this session actually
discussed. This is the single source of truth for that procedure — the `update-knowledge`
Stop hook points the agent here, and the user can run `/update-knowledge` manually. Keep
the two in sync by editing only this file.

## Procedure

1. **Locate the glossary.** Read `KNOWLEDGE.md` at the repo root. If a `KNOWLEDGE-MAP.md`
   exists instead, resolve which area file(s) the session touched and read those. If no
   glossary file exists yet and the session pinned down at least one real domain term,
   create `KNOWLEDGE.md` now (follow the `deep-discuss` skill's `KNOWLEDGE-FORMAT.md`).

2. **List the session's domain terms.** Scan this conversation for every domain term that
   came up — names of entities, concepts, states, roles, or relationships specific to this
   project. Ignore generic programming vocabulary; capture only language a newcomer to
   _this domain_ would need defined.

3. **Mark each term.** For every term, classify it:
   - **recorded** — already in the glossary with a definition matching how it was used.
   - **updated** — in the glossary but the session sharpened, renamed, or contradicted it.
   - **missing** — discussed and pinned down, but absent from the glossary.

4. **Write the gaps.** Add every **missing** term and rewrite every **updated** one,
   following the existing format. Keep entries to a glossary definition — no implementation
   detail, spec text, or scratch notes.

5. **Report.** Show a one-line summary of what changed, e.g.
   `KNOWLEDGE.md: +preview-lane / ~worktree-db redefined`, or state plainly that nothing
   needed changing.

## Guardrails

- If the session genuinely introduced no new or changed domain language, say so and make
  no edits — do not invent entries to look productive.
- A term clarified only loosely ("we sort of mean X") is not yet pinned — leave it out and
  flag it as still-fuzzy rather than recording a guess.
