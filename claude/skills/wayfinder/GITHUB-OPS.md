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

## Create implementation tickets in dependency order

For the **Roadmap the build** phase. Creating blockers first means every edge can be wired the moment its issue exists, with no second pass to forget. The roadmap's Needs column is the input; sort it topologically before you start.

**macOS ships bash 3.2, which has no `declare -A`.** A failed `declare -A` degrades silently into an indexed array, and the ticket-to-issue map then returns empty strings with no error. Keep the map in a JSON file and let Python own the loop:

```bash
REPO=$(gh repo view --json nameWithOwner --jq .nameWithOwner)
# tickets.json: topologically sorted. Each entry: {"ticket": 8, "title": "...", "body_file": "t8.md", "needs": [3, 6]}
python3 - "$REPO" <<'EOF'
import json, subprocess, sys
repo = sys.argv[1]
issues = {}                                   # roadmap ticket -> issue number
def gh(*args): return subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout.strip()
for t in json.load(open("tickets.json")):
    url = gh("issue", "create", "--title", t["title"], "--body-file", t["body_file"])
    num = int(url.rsplit("/", 1)[1]); issues[t["ticket"]] = num
    for need in t["needs"]:
        blocker_id = gh("api", f"repos/{repo}/issues/{issues[need]}", "--jq", ".id")   # database id, not the number
        gh("api", "--method", "POST", f"repos/{repo}/issues/{num}/dependencies/blocked_by", "-F", f"issue_id={blocker_id}")
json.dump(issues, open("issues.json", "w"), indent=1)
EOF
```

Needs that are already closed get wired too. The native relationship is the record, GitHub accepts a closed blocker, and the frontier query still reads it as satisfied.

### Make body edits idempotent

A **Can start when** line is inserted once. Check for it before inserting, so a re-run (or a second session repairing a batch) doesn't stack duplicates:

```bash
gh issue view "$NUM" --json body --jq .body > body.md
if ! grep -q '^\*\*Can start when:\*\*' body.md; then
  python3 - body.md "$LINE" <<'EOF'
import sys; path, line = sys.argv[1], sys.argv[2]
text = open(path).read()
head, _, rest = text.partition("\n\n")           # insert after the first paragraph (the roadmap pointer)
open(path, "w").write(f"{head}\n\n{line}\n\n{rest}")
EOF
  gh issue edit "$NUM" --body-file body.md
fi
```

### Verify after linking

Compare every issue's native `blocked_by` numbers with the roadmap's Needs before you call the batch done. Edges go missing when a create fails mid-loop or a database id lookup returns empty:

```bash
python3 - "$REPO" <<'EOF'
import json, subprocess, sys
repo = sys.argv[1]
issues = {int(k): v for k, v in json.load(open("issues.json")).items()}   # roadmap ticket -> issue number
for t in json.load(open("tickets.json")):
    num = issues[t["ticket"]]
    out = subprocess.run(["gh", "api", f"repos/{repo}/issues/{num}/dependencies/blocked_by", "--jq", "[.[].number]"], capture_output=True, text=True, check=True).stdout
    actual = sorted(json.loads(out)); expected = sorted(issues[n] for n in t["needs"])
    print(("ok  " if actual == expected else "MISMATCH ") + f"#{num}: blocked_by={actual} needs={expected}")
EOF
```

Fix any `MISMATCH` line by wiring the missing edge (the POST is idempotent) before linking the issues from the roadmap.

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
