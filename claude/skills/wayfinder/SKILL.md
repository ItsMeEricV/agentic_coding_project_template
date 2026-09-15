---
name: wayfinder
description: Chart a chunk of work too big for one agent session as a shared map of decision tickets on GitHub Issues, then resolve them one at a time until the way to the destination is clear. Use when an idea is large and foggy — "chart a map", "wayfind this", "too big to plan in one session" — or when invoked with an existing wayfinder map.
disable-model-invocation: true
---

A loose idea has arrived, too big for one agent session, and wrapped in fog: the way from here to the **destination** isn't visible yet. Wayfinding is about finding that way, not charging at the destination. This skill charts the way as a **shared map** on the repo's GitHub Issues, then works its **decision tickets** (questions whose resolution is a decision, not slices of a build to execute) one at a time until the route is clear.

The destination varies per effort, and naming it is the first act of charting: it shapes every ticket. It might be a spec to hand off and iterate on, a decision to lock before planning starts, or a change made in place like a data-structure migration. The map is domain-agnostic: engineering work, course content, whatever fits the shape.

> Adapted from [Matt Pocock's `wayfinder` skill](https://github.com/mattpocock/skills/blob/main/skills/engineering/wayfinder/SKILL.md), rewired onto this repo's primitives: `deep-discuss` for the grilling, `docs/rfc/` for decisions that earn a record, `KNOWLEDGE.md` for the vocabulary, and GitHub Issues as the one tracker.

## Ask before you open a single issue

`AGENTS.md` and the global rules are unambiguous: **never create a GitHub issue without explicit user permission.** A map is issues — often a dozen of them — so this skill has one approval gate and it is not optional.

Before creating anything, present the whole proposed map in chat: the destination, the ticket titles with their types, the blocking edges, and the fog. Then wait for an explicit yes. On approval, create the batch. Adding a ticket mid-effort during **Work through the map** is covered by that same yes, provided the user is in the session and sees it happen — a batch created while they are away is not.

This is also why the frontmatter carries `disable-model-invocation: true`. Wayfinder runs when a human asks for it, never because a prompt looked map-shaped.

## Plan, don't do

Wayfinder is **planning** by default: each ticket resolves a decision, and the map is done when the way is clear, with nothing left to decide before someone goes and does the thing. The pull to just do the work is usually the signal you've reached the edge of the map and it's time to hand off — reach for the `handoff` skill there. An effort can override this in its **Notes**, carrying execution into the map itself, but absent that, produce decisions, not deliverables.

## Refer by name

Every map and ticket is an issue, so it has a **name**: its title. In everything the human reads (narration, the map's Decisions-so-far), refer to it by that name, never by a bare id, number, or slug. A wall of `#42, #43, #44` is illegible; names read at a glance. The number and URL don't vanish; a name wraps its link, but they ride _inside_ the name, never stand in for it.

## The Map

The map is a single GitHub issue on this repo, labelled `wayfinder:map`, the canonical artifact. Its tickets are sub-issues of the map.

The map is an **index**, not a store. It lists the decisions made and points at the tickets that hold their detail; a decision lives in exactly one place, its ticket, so the map never restates it, only gists it and links.

Every GitHub operation this skill needs — creating the labels, attaching sub-issues, wiring blocking edges, querying the frontier — is spelled out in [GITHUB-OPS.md](./GITHUB-OPS.md). Read it before touching the tracker; the sub-issue and dependency endpoints take a database id that is **not** the number in the URL, and that trips every first attempt.

### The map body

The whole map at low resolution, loaded once per session. Open tickets are **not** listed: they are open sub-issues, found by query.

```markdown
## Destination

<what reaching the end of this map looks like: the spec, decision, or change this effort is finding its way to. One or two lines; every session orients to it before choosing a ticket.>

## Notes

<domain; skills every session should consult; standing preferences for this effort>

## Decisions so far

<!-- the index: one line per closed ticket, enough to judge relevance, then zoom the link for the detail the ticket holds -->

- [<closed ticket title>](link): <one-line gist of the answer>

## Not yet specified

<!-- see "Fog of war": in-scope fog you can't ticket yet; graduates as the frontier advances -->

## Out of scope

<!-- see "Out of scope": work ruled beyond the destination; closed, never graduates -->
```

### Tickets

Each ticket is a **sub-issue** of the map; the issue number is its identity. Its body is the question, sized to one 100K token agent session:

```markdown
## Question

<the decision or investigation this ticket resolves>
```

Each ticket carries a `wayfinder:<type>` label, one of `research`, `prototype`, `grilling`, `task` (see [Ticket Types](#ticket-types)).

A session **claims** a ticket by assigning it to the dev driving the map, **first**, before any work, so concurrent sessions skip it. That assignee _is_ the claim: an open, unassigned ticket is unclaimed.

Blocking uses GitHub's **native** issue dependencies (`blocked by` / `blocks`), not a body convention: the native relationship renders the frontier _visually_ in GitHub's own UI, so the human sees what's takeable without opening the map. A ticket is **unblocked** when every ticket blocking it is closed; the **frontier** is the open, unblocked, unassigned sub-issues, the edge of the known.

The answer isn't part of the body; it's recorded on resolution (see [Work through the map](#work-through-the-map)). Assets created while resolving a ticket are linked from the issue, not pasted in.

## Ticket Types

Every ticket is either **HITL** (human in the loop, worked _with_ a human who speaks for themselves) or **AFK**, driven by the agent alone. A HITL ticket only resolves through that live exchange; the agent never stands in for the human's side of it (an agent that grills itself and answers its own questions has broken this).

- **Grilling** (HITL): Conversation. The default case. Invoke the `deep-discuss` skill and run it as written — it scopes the decision tree, holds the user to `KNOWLEDGE.md`, and updates the glossary inline as terms pin down. The ticket's **Question** is the topic you hand it.
- **Research** (AFK): Reading documentation, third-party APIs, or local resources to surface a fact a decision waits on. Use when knowledge outside the current working directory is required. Resolve it by dispatching an `Explore` subagent (codebase and local docs) or a `general-purpose` subagent with web access (third-party APIs, vendor docs), asking for the fact and its source, not a recommendation. Prefer Context7 over web search for library documentation. Findings land in the resolution comment; anything longer than a comment goes on a throwaway `research/<name>` branch with a link from the ticket.
- **Prototype** (HITL): Raise the fidelity of the discussion by making a cheap, rough, concrete artifact to react to — an outline, a rough take, a stub, UI or logic code. Use when "how should it look" or "how should it behave" is the key question. Build it on a throwaway `wayfinder/<ticket-slug>` branch or in the scratchpad, show it, and let the reaction be the decision. It is a prop, not a deliverable: do not polish it, do not merge it, and link it from the issue rather than pasting it in.
- **Task** (HITL or AFK): Manual work that must happen before a _decision_ can be made: nothing to decide, prototype, or research, but the discussion is blocked until it's done. Signing up for a service so its API can be judged, provisioning access, moving data so its shape can be seen. This is the one type that _does_ rather than decides, and it earns its place by unblocking a decision, not by delivering the destination. The agent drives it alone where it can (AFK); otherwise it hands the human a precise checklist (HITL). Resolved when the work is done; the answer records what was done and any resulting facts (where credentials live, new URLs, row counts) later tickets depend on.

## Fog of war

The map is _deliberately_ incomplete: don't chart what you can't yet see. Beyond the live tickets lies the **fog of war**: the dim view of decisions and investigations you can tell are coming but can't yet pin down, because they hang on questions still open. Resolving a ticket clears the fog ahead of it, graduating whatever's now specifiable into fresh tickets, one at a time, until the way to the destination is clear and no tickets remain.

The map's **Not yet specified** section is where that dim view is written down: the suspected question, the area to revisit later. It's the undiscovered frontier _toward_ the destination: everything here is in scope, just not sharp enough to ticket. Write as loosely or as fully as the view allows; it doubles as a signpost for collaborators reading where the effort is headed.

**Fog or ticket?** The test is whether you can state the question precisely now, _not_ whether you can answer it now.

- **Ticket when** the question is already sharp, even if it's blocked and you can't act on it yet.
- **Not yet specified when** you can't yet phrase it that sharply. Don't pre-slice the fog into ticket-sized pieces: it's coarser than a ticket, and one patch may graduate into several tickets, or none, once the frontier reaches it.

**Not yet specified** excludes what's already decided (Decisions so far), what's already a live ticket, and what's out of scope (the next section).

## Out of scope

Fog only ever gathers _toward_ the destination. The destination fixes the scope, so work beyond it is **out of scope**: it isn't fog, and it doesn't belong in **Not yet specified**. It gets its own **Out of scope** section on the map: work you've consciously ruled out of _this_ effort. Scope, not sharpness, lands it here.

Out-of-scope work never graduates (the frontier stops at the destination), so it returns only if the destination is redrawn, and then as a fresh effort, not a resumption.

Ruling something out of scope is a scoping act, not a step on the route. When a ticket that already exists turns out to sit past the destination (mis-scoped in while charting, or exposed by a resolution), **close it as not planned** (a closed ticket is unambiguously off the frontier) and leave one line in the **Out of scope** section: the gist plus why it's out of scope, linking the closed ticket. It stays out of **Decisions so far**, which records the route actually walked; a scope boundary isn't a step on it.

## Decisions that earn an RFC

A resolution comment is enough for most tickets. A few decisions are load-bearing enough that a future reader will need the reasoning, and those graduate to an RFC in `docs/rfc/`. The bar is `deep-discuss`'s, unchanged — all three must hold:

1. **Hard to reverse** — changing your mind later carries a real cost.
2. **Surprising without context** — a future reader will ask "why was it done this way?"
3. **The outcome of a genuine trade-off** — there were real alternatives and one was chosen for specific reasons.

When they do, write the RFC following [RFC-FORMAT.md](../deep-discuss/RFC-FORMAT.md), commit it, and make the resolution comment point at it rather than restating it. The map's Decisions-so-far line then gists the decision and links the ticket as usual — the ticket links the RFC, so the detail still lives in exactly one place.

Terms the effort pins down go to `KNOWLEDGE.md` as `deep-discuss` prescribes, inline, the moment they land. A map that ends with a stale glossary has leaked its own vocabulary.

## Invocation

Two modes. Either way, **never resolve more than one ticket per session**, with the exception of research tickets.

### Chart the map

User invokes with a loose idea.

1. **Name the destination.** Invoke `deep-discuss` to pin down what this map is finding its way to: the spec, decision, or change. The destination fixes the scope, so it's settled first.
2. **Map the frontier.** Grill again, **breadth-first** this time: fan out across the whole space rather than deep on any one thread, surfacing the open decisions and the first steps takeable now. **If this surfaces no fog** (the way to the destination is already clear, the whole journey small enough for one session), you don't need a map. Stop and ask the user how they'd like to proceed — plan mode or a single `deep-discuss` pass is the cheaper tool.
3. **Propose the whole map in chat and wait for an explicit yes** (see [Ask before you open a single issue](#ask-before-you-open-a-single-issue)): destination, ticket titles and types, blocking edges, fog.
4. **Create the map issue** (label `wayfinder:map`): Destination and Notes filled in, Decisions-so-far empty, the fog sketched into **Not yet specified**.
5. **Create the tickets you can specify now**, attach each as a sub-issue of the map, then wire blocking edges in a **second pass** (issues need numbers before they can reference each other). Wiring sorts them into the frontier and the blocked; everything you can't yet specify stays in the fog: the **Not yet specified** section.
6. **Fire the research subagents.** For each `research` ticket you just created, dispatch a subagent in parallel to resolve it, capturing its findings on a throwaway `research/<name>` branch with a pointer from the ticket.
7. Stop: charting is one session's work; it hand-resolves nothing.

### Work through the map

User invokes with a map (URL or number). A ticket is **optional**: without one, you pick the next decision, not the user.

1. Load the **map**: the low-res view, not every ticket body.
2. Choose the ticket. If the user named one, use it. Otherwise take the first frontier ticket in order. **Claim it**: assign it to yourself before any work.
3. Resolve it. **Zoom as needed**: fetch the full body of any related or closed ticket on demand; invoke whichever skills the `## Notes` block names. If in doubt, invoke `deep-discuss`.
4. Record the resolution: post the answer as a **resolution comment**, write an RFC if the decision [earns one](#decisions-that-earn-an-rfc), **close** the issue, and **append a context pointer** to the map's Decisions-so-far.
5. Add newly-surfaced tickets (create-then-wire); graduate any fog the answer has made specifiable, clearing each graduated patch from **Not yet specified** so it lives only as its new ticket. If the answer reveals that a ticket (this one or another) sits beyond the destination, **rule it out of scope** rather than resolving it on the route. If the decision invalidates other parts of the map, update or delete those tickets.

The user may run unblocked tickets in parallel, so expect other sessions to be editing the tracker concurrently. Re-read an issue immediately before you edit it rather than trusting a body you loaded at the top of the session.
