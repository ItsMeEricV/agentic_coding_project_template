# What to Watch

The What to Watch block is machine-read. After the deploy, a loop agent in the same harness polls each item's `source`, evaluates `expect`, and alerts the user on a breach. It cannot ask the author what was meant, so every field has to be executable as written. A guessed threshold or an invented query doesn't just fail quietly — it either pages the user for nothing or misses a real regression. `watch: none` with an honest reason is always better than a weak item.

## Schema

```yaml
watch:
  - id: orders-create-5xx # kebab-case, unique within the PR
    kind: regression # regression | should_not | success
    source: axiom # one of the sources declared in AGENTS.md
    query: '...' # literal query in the source's own syntax
    expect: value <= baseline * 2 # value <op> <number> | value <op> baseline | value <op> baseline * <k>
    baseline: prior_7d # prior_7d | none
    window: 24h # 1h | 6h | 12h | 24h | 48h
    ref: src/app/api/orders/route.ts:41 # file:line of the emitter being counted
    observed: { value: 3, at: 2026-10-10 } # required when baseline != none
```

Or, when nothing qualifies:

```yaml
watch: none
reason: docs-only change; no production code path touched
```

### Field rules

- **`kind`** — `regression`: an existing signal must not get worse. `should_not`: a signal must stay at zero (a new error class, a deprecated path still being hit); defaults to `expect: value == 0`. `success`: the new behaviour is observed firing. Pick the kind first; it determines how the loop agent judges the item (see Judging).
- **`source`** — must be one of the observability sources the project declares in `AGENTS.md` (project file first, then the user-level `~/.claude/CLAUDE.md`; the project list wins outright when present). Each declared source names the tool the loop agent calls. Confirm that tool is in your roster before writing the item — if it isn't, the item is unobservable and has to go.
- **`query`** — the literal query string the source accepts (APL for Axiom, Sentry search syntax, SQL for `pg_stat_statements`). Prose is allowed only when the source has no query language, and then it names the exact view and filters. Prose that needs re-interpretation at deploy time is where drift creeps in.
- **`expect`** — operators `> >= < <= == !=` (a single `=` means `==`). An absolute number is allowed only when `observed` shows where it came from.
- **`baseline`** — `prior_7d` means the same query over the 7 days before the deploy, scaled to the window. `none` means `expect` is absolute. Any baseline you didn't measure is a guess, so `baseline != none` makes `observed` mandatory.
- **`window`** — how long after 100% rollout (or the feature flag reaching 100%) before `success` is judged, and the maximum span `regression` / `should_not` are watched.
- **`ref`** — the `file:line` of the code that emits what the query counts. It must be in this PR's diff, or at most one call-graph hop from it. This is the provenance that stops items drifting away from the change. `n/a` is tolerated only for pre-existing platform metrics, and then cite the existing emitter where you can.
- **`observed`** — what the query returned when you dry-ran it over the prior 7 days on `main`. Optional when `baseline: none`, required otherwise.

Max 3 items. Keep the ones that would actually make the user act.

## Judging (for the loop agent)

- `regression` and `should_not`: evaluated continuously across the window. A breach that holds on two consecutive polls → alert.
- `success`: evaluated once, at window end. Unmet → alert.
- An item whose `source` tool is not in the loop agent's roster is skipped with a terminal note. It is never treated as satisfied.

## Alerting

On a breach, do both:

1. `PushNotification` — harness-native, zero setup, reaches the desktop (and the phone when Remote Control is connected). It suppresses itself when the user is active in the terminal, so it is the floor, not the whole answer.
2. Post to the deploy-alert destination declared in `AGENTS.md` (project first, then user-level). The default is a Discord webhook read from `DISCORD_ALERT_WEBHOOK_URL` in `~/.claude/channels/discord/.env`:

   ```bash
   set -a; . ~/.claude/channels/discord/.env; set +a
   curl -s -H 'Content-Type: application/json' -d '{"content":"<id>: <expect> breached — <value> vs <baseline>"}' "$DISCORD_ALERT_WEBHOOK_URL"
   ```

If no destination is declared anywhere, alert via `PushNotification` only and say so once in the terminal.

## Preflight (author, before opening the PR)

Run this before drafting the body. Author and loop agent share the harness, so a check that passes now means the loop can act later.

1. Resolve the alert destination. Declared but unreachable (env file missing, tool absent) → **stop**. Tell the user to fix the wiring or change the declaration. Do not open the PR.
2. Resolve the observability sources. For each, confirm the named tool is in your roster. Drop any source that isn't, and note it in the terminal.
3. Derive candidate items from the diff: routes from changed handlers, external APIs from changed client calls, DB statements from changed queries or schema. Use `graft callers <symbol>` for the one-hop neighbours. Nothing beyond one hop.
4. For each candidate, write the literal query and dry-run it over the prior 7 days on `main`. Record `observed`. If the query can't be run, the item has no evidence and is dropped.
5. Keep at most 3. If nothing survives, write `watch: none` with the reason.
