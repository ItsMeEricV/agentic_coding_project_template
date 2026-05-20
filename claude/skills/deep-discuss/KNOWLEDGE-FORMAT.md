# KNOWLEDGE.md Format

`KNOWLEDGE.md` is the project's shared-understanding document: a glossary of domain terms plus the common understandings that make conversations precise. It is not a spec and not a scratch pad.

## Structure

```md
# {Area Name}

{One or two sentences on what this area covers and why it exists.}

## Language

**Order**:
A confirmed request from a customer for one or more items.
_Avoid_: Purchase, transaction

**Invoice**:
A request for payment sent to a customer after delivery.
_Avoid_: Bill, payment request

**Customer**:
A person or organization that places orders.
_Avoid_: Client, buyer, account

## Flagged ambiguities

**"Account"** — used for both the billing relationship and the login identity.
Resolution: use **Customer** for the billing relationship, **User** for the login identity.

## Example dialogue

> **Dev:** If a Customer cancels one item, does the whole Order die?
> **Domain expert:** No — the Order stays open, that line item moves to Cancelled.
> The Invoice is only generated once the remaining items ship.
```

## Rules

- **Be opinionated.** When several words name the same concept, pick the best one and list the rest under _Avoid_.
- **Flag conflicts explicitly.** When a term is used ambiguously, record it under "Flagged ambiguities" with a clear resolution.
- **Keep definitions tight.** One or two sentences. Define what the term *is*, not what it *does*.
- **Show relationships.** Bold the term names and express cardinality where it is obvious.
- **Only project-specific terms belong here.** General programming concepts (timeouts, retries, error types, utility patterns) do not, even if the project leans on them heavily. Before adding a term, ask: is this unique to this project's domain, or is it general programming vocabulary? Only the former belongs.
- **Group terms under subheadings** when natural clusters appear. A flat list is fine if everything belongs to one cohesive area.
- **Write an example dialogue.** A short exchange between a dev and a domain expert that shows the terms interacting naturally and clarifies the boundaries between related concepts.

## Single area vs. multiple areas

**Single area (most repos):** one `KNOWLEDGE.md` at the repo root.

**Multiple areas:** a `KNOWLEDGE-MAP.md` at the repo root lists each area, where it lives, and how the areas relate:

```md
# Knowledge Map

## Areas

- [Ordering](./src/ordering/KNOWLEDGE.md) — receives and tracks customer orders
- [Billing](./src/billing/KNOWLEDGE.md) — generates invoices and processes payments
- [Fulfillment](./src/fulfillment/KNOWLEDGE.md) — manages warehouse picking and shipping

## Relationships

- **Ordering → Fulfillment**: Ordering emits `OrderPlaced` events; Fulfillment consumes them to start picking
- **Fulfillment → Billing**: Fulfillment emits `ShipmentDispatched` events; Billing consumes them to generate invoices
- **Ordering ↔ Billing**: shared types for `CustomerId` and `Money`
```

Infer which structure applies:

- `KNOWLEDGE-MAP.md` exists → read it to find the areas
- only a root `KNOWLEDGE.md` exists → single area
- neither exists → create a root `KNOWLEDGE.md` lazily when the first term is resolved
