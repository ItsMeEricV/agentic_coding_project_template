# RFC Format

An RFC (Request for Comments) records *that* a decision was made and *why*. RFCs live in `docs/rfc/` with sequential numbering: `0001-slug.md`, `0002-slug.md`, and so on.

Create the `docs/rfc/` directory lazily — only when the first RFC is needed.

## Template

```md
# {Short title of the decision}

{1-3 sentences: what the context was, what was decided, and why.}
```

That is the whole template. An RFC can be a single paragraph. The value is in capturing the decision and its reasoning — not in filling out sections.

## Optional sections

Add these only when they earn their place. Most RFCs need none of them.

- **Status** frontmatter (`proposed | accepted | deprecated | superseded by RFC-NNNN`) — useful once decisions start getting revisited
- **Considered options** — only when the rejected alternatives are worth remembering
- **Consequences** — only when non-obvious downstream effects need to be called out

## Numbering

Scan `docs/rfc/` for the highest existing number and increment by one.

## When to offer an RFC

All three must be true:

1. **Hard to reverse** — changing your mind later carries a real cost
2. **Surprising without context** — a future reader will look at the code and wonder "why on earth was it done this way?"
3. **The outcome of a genuine trade-off** — there were real alternatives and one was chosen for specific reasons

If a decision is easy to reverse, skip it — you will just reverse it. If it is not surprising, nobody will wonder why. If there was no real alternative, there is nothing to record beyond "we did the obvious thing."

### What qualifies

- **Architectural shape.** "We use a monorepo." "The write model is event-sourced; the read model is projected into Postgres."
- **Integration patterns between areas.** "Ordering and Billing communicate via domain events, not synchronous HTTP."
- **Technology choices that carry lock-in.** Database, message bus, auth provider, deployment target — not every library, just the ones that would take a quarter to swap out.
- **Boundary and scope decisions.** "Customer data is owned by the Customer area; other areas reference it by ID only." The explicit no's matter as much as the yes's.
- **Deliberate deviations from the obvious path.** "We use hand-written SQL instead of an ORM because X." Anything where a reasonable reader would assume the opposite — this stops the next engineer from "fixing" something that was intentional.
- **Constraints not visible in the code.** "We can't use AWS because of compliance requirements." "Responses must stay under 200ms because of the partner API contract."
- **Rejected alternatives where the rejection is non-obvious.** If GraphQL was considered and REST was chosen for subtle reasons, record it — otherwise someone will propose GraphQL again in six months.
