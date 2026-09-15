# Wayfinding operations on GitHub Issues

Every tracker operation the `wayfinder` skill needs, as `gh` commands. Read this before touching the tracker.

## The one gotcha

The sub-issue and dependency endpoints take an issue's **database id**, not the number in its URL and not the GraphQL node id:

```bash
REPO=$(gh repo view --json nameWithOwner --jq .nameWithOwner)
gh api "repos/$REPO/issues/37" --jq .id     # → 5294014150   ✅ database id
gh issue view 37 --json id --jq .id          # → I_kwDO…     ❌ node id, rejected
```

Resolve the database id every time you wire a relationship. `$REPO` below is always that `nameWithOwner` value.

## One-time setup per repo

Labels are cheap and `--force` is idempotent, so just run this when charting a map in a repo for the first time:

```bash
gh label create "wayfinder"           --color 1D76DB --description "Created by the wayfinder skill" --force
gh label create "wayfinder:map"       --color 5319E7 --description "A wayfinder map"            --force
gh label create "wayfinder:grilling"  --color BFD4F2 --description "Wayfinder: conversation"    --force
gh label create "wayfinder:research"  --color BFD4F2 --description "Wayfinder: find a fact"     --force
gh label create "wayfinder:prototype" --color BFD4F2 --description "Wayfinder: build a prop"    --force
gh label create "wayfinder:task"      --color BFD4F2 --description "Wayfinder: unblocking work" --force
```

Every issue the skill creates carries **two** labels: the umbrella `wayfinder` plus its specific one (`wayfinder:map` or a `wayfinder:<type>`). The umbrella is what makes the effort legible from outside — one query finds everything wayfinder has ever opened in the repo, without OR-ing five labels or knowing a map number:

```bash
gh issue list --label "wayfinder" --state all --limit 200   # everything the skill has opened
gh issue list --label "wayfinder:map" --state open          # the live maps
```

It also gives the human one label to filter out of their ordinary backlog views, so a map's dozen decision tickets don't drown the real work.

## Create the map

Write the body to a file first — heredocs inside `--body` mangle markdown.

```bash
gh issue create --title "<destination name>" --label "wayfinder" --label "wayfinder:map" --body-file map.md
```

## Create a ticket and attach it to the map

Two steps: create the issue, then attach it as a sub-issue by database id.

```bash
TICKET_URL=$(gh issue create --title "<question as a title>" --label "wayfinder" --label "wayfinder:grilling" --body-file ticket.md)
TICKET_NUM=${TICKET_URL##*/}
TICKET_ID=$(gh api "repos/$REPO/issues/$TICKET_NUM" --jq .id)
gh api --method POST "repos/$REPO/issues/$MAP_NUM/sub_issues" -F sub_issue_id="$TICKET_ID"
```

## Wire a blocking edge

Second pass, after every ticket exists. `blocked_by` reads "this issue is blocked by that one".

```bash
BLOCKER_ID=$(gh api "repos/$REPO/issues/$BLOCKER_NUM" --jq .id)
gh api --method POST "repos/$REPO/issues/$BLOCKED_NUM/dependencies/blocked_by" -F issue_id="$BLOCKER_ID"
```

GitHub renders the result as native `Blocked by` / `Blocks` relationships, which is the point: the human sees what's takeable in the UI without opening the map.

## Load the map

```bash
gh issue view "$MAP_NUM" --json number,title,body,url
```

The map body is the low-res view. Do not pull every ticket body — zoom into individual tickets on demand.

## List the map's tickets

```bash
gh api "repos/$REPO/issues/$MAP_NUM/sub_issues" \
  --jq '.[] | {number, title, state, assignee: (.assignee.login // null), labels: [.labels[].name]}'
```

## Query the frontier

Open, unblocked, unassigned. One pass over the children, checking each one's open blockers:

```bash
gh api "repos/$REPO/issues/$MAP_NUM/sub_issues" \
  --jq '.[] | select(.state=="open") | select(.assignee==null) | [.number, .title] | @tsv' |
while IFS=$'\t' read -r num title; do
  blockers=$(gh api "repos/$REPO/issues/$num/dependencies/blocked_by" --jq '[.[] | select(.state=="open")] | length')
  [ "$blockers" -eq 0 ] && printf '%s\t%s\n' "$num" "$title"
done
```

Frontier order is the order this returns: sub-issue order on the map, which is creation order unless someone has reordered it in the UI.

## Claim a ticket

Before any work, so concurrent sessions skip it:

```bash
gh issue edit "$TICKET_NUM" --add-assignee @me
```

## Resolve a ticket

```bash
gh issue comment "$TICKET_NUM" --body-file answer.md
gh issue close "$TICKET_NUM"
```

Then append the one-line gist plus link to the map's **Decisions so far**. Re-read the map body immediately before editing it — other sessions may have appended since you loaded it:

```bash
gh issue view "$MAP_NUM" --json body --jq .body > map.md
# edit map.md
gh issue edit "$MAP_NUM" --body-file map.md
```

## Rule a ticket out of scope

Closing as `not planned` is what distinguishes a scope boundary from a decision on the route:

```bash
gh issue close "$TICKET_NUM" --reason "not planned" --comment "Out of scope: <why>"
```

Then add the one-liner to the map's **Out of scope** section, not **Decisions so far**.

## Fallback

If GitHub's sub-issue or dependency endpoints are unavailable (an enterprise instance behind on features, a token without `issues:write`), fall back to a body convention — a `## Tickets` checklist on the map and a `Blocked by: #N` line in each ticket body — and say so in the map's **Notes**, so later sessions don't hunt for relationships that were never wired.
