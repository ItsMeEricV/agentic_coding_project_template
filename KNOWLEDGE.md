# KNOWLEDGE.md: the project glossary

This file is the project's **shared-understanding document**: a glossary of domain terms plus the common understandings that keep conversations precise. When you and an agent use the same words to mean the same things, plans stop drifting.

## Purpose

- Pin down the **canonical name** for every domain concept, so the codebase, the docs, and the conversation all agree.
- Surface **ambiguity** — words that get used loosely or mean two things — and resolve it explicitly.
- Give a new agent (or new teammate) the project's vocabulary in one read.

## What does NOT belong here

KNOWLEDGE.md is a glossary, nothing else. Keep it devoid of implementation detail.

- **The "what"** → `SPEC.md`. **The "where/how"** → `ARCHITECTURE.md` / `AGENTS.md`. **Quirks and gotchas** → `MEMORY.md`.
- General programming vocabulary (timeout, retry, idempotent, cache) does **not** belong here even if the project leans on it. Before adding a term, ask: is this unique to *this project's domain*, or is it general engineering vocabulary? Only the former belongs.

## Structure

### Language

Define each domain term in one or two sentences — what it **is**, not what it **does**. Be opinionated: when several words name the same concept, pick the best one and list the rest under _Avoid_.

> **Order**:
> A confirmed request from a customer for one or more items.
> _Avoid_: Purchase, transaction
>
> **Customer**:
> A person or organization that places orders.
> _Avoid_: Client, buyer, account

Group terms under subheadings when natural clusters emerge. A flat list is fine when everything belongs to one cohesive area.

### Flagged ambiguities

When a term is used to mean two different things, call it out with a clear resolution.

> **"Account"** — used for both the billing relationship and the login identity.
> Resolution: use **Customer** for the billing relationship, **User** for the login identity.

### Example dialogue

Write a short exchange between a dev and a domain expert that shows the terms interacting naturally and clarifies the boundaries between related concepts.

> **Dev:** If a Customer cancels one item, does the whole Order die?
> **Domain expert:** No — the Order stays open, that line item moves to Cancelled. The Invoice is only generated once the remaining items ship.

## Multiple areas of knowledge

Most projects need a single `KNOWLEDGE.md` at the repo root. If the project grows into clearly separate domains, add a `KNOWLEDGE-MAP.md` at the root that lists each area, where its `KNOWLEDGE.md` lives, and how the areas relate:

```md
# Knowledge Map

## Areas

- [Ordering](./src/ordering/KNOWLEDGE.md) — receives and tracks customer orders
- [Billing](./src/billing/KNOWLEDGE.md) — generates invoices and processes payments

## Relationships

- **Ordering → Billing**: Ordering emits `OrderPlaced` events; Billing consumes them to generate invoices
```

## Maintenance

This file is kept current as the project's language is sharpened — most often during a `deep-discuss` session, which challenges plans against this glossary and writes resolved terms back here inline. When a term is renamed or retired, update it here so the glossary never lies.
