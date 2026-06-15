#!/usr/bin/env bash
# Stop hook — nudges the agent to reconcile KNOWLEDGE.md when the branch
# introduces a new domain TYPE that no KNOWLEDGE*.md documents yet.
#
# Signal: the diff, not the conversation. The first iteration grepped the
# transcript for cue phrases and fired constantly (a UI bugfix that merely
# mentioned domain nouns tripped it). This version keys off durable artifacts:
# new `type`/`interface`/`enum`/Prisma `model`/Zod schema declarations on the
# branch whose name doesn't already appear in a glossary file. A session that
# adds no new domain type stays silent. It does NOT restate the reconcile
# procedure — it points at commands/update-knowledge.md (run as
# /update-knowledge).
#
# Fires (blocks the stop once) only when ALL hold:
#   - a KNOWLEDGE.md / KNOWLEDGE-MAP.md exists in the repo (and isn't an
#     unseeded template carrying the 'knowledge-reconcile:skip' marker)
#   - the branch diff adds a domain-type name not found in any KNOWLEDGE*.md
#   - no KNOWLEDGE*.md was already modified this session (maintained inline)
#   - we haven't already nudged this session (once-per-session marker)
#   - we're not already inside a Stop-hook continuation (stop_hook_active)
#
# Stop blocking contract: emit {"decision":"block","reason":...} on stdout
# with exit 0. Any other path exits 0 silently and lets the stop proceed.

set -euo pipefail

input=$(cat)

# stop_hook_active is true when we're already in a continuation we triggered.
# Bail so the agent can actually finish after doing the reconcile.
active=$(printf '%s' "$input" | jq -r '.stop_hook_active // false')
[ "$active" = "true" ] && exit 0

session_id=$(printf '%s' "$input" | jq -r '.session_id // empty')
cwd=$(printf '%s' "$input" | jq -r '.cwd // empty')
[ -z "$cwd" ] && exit 0

repo=$(git -C "$cwd" rev-parse --show-toplevel 2>/dev/null || true)
[ -z "$repo" ] && exit 0

# Only nag repos that already keep a glossary.
root_glossary=""
for f in KNOWLEDGE.md KNOWLEDGE-MAP.md; do
  [ -f "$repo/$f" ] && root_glossary="$repo/$f" && break
done
[ -z "$root_glossary" ] && exit 0

# Skip an unseeded template glossary: the shipped KNOWLEDGE.md is a guide about
# how to write a glossary, not a real one, and carries a
# 'knowledge-reconcile:skip' marker until the project seeds real terms.
grep -qiF 'knowledge-reconcile:skip' "$root_glossary" && exit 0

# Once-per-session marker.
marker="${TMPDIR:-/tmp}/claude-knowledge-reconcile-${session_id:-nosession}.done"
[ -f "$marker" ] && exit 0

# If a KNOWLEDGE*.md is already dirty in the working tree, assume the agent
# maintained it inline this session — nothing to nudge about.
if git -C "$repo" status --porcelain 2>/dev/null | grep -qiE 'KNOWLEDGE[A-Z-]*\.md$'; then
  exit 0
fi

# --- Diff signal: new domain types not in any glossary -----------------------
# Diff the whole branch (base..worktree, including uncommitted) so a type added
# earlier in the branch still counts. On the default branch this degrades to
# uncommitted-vs-HEAD.
default_branch=main
git -C "$repo" show-ref --verify -q refs/heads/main || default_branch=master
base=$(git -C "$repo" merge-base HEAD "$default_branch" 2>/dev/null || true)
[ -z "$base" ] && base=HEAD

added=$(git -C "$repo" diff "$base" -- '*.ts' '*.tsx' '*.prisma' 2>/dev/null \
  | grep -E '^\+' | grep -vE '^\+\+\+' || true)
[ -z "$added" ] && exit 0

# Extract declared type names from added lines. Domain types are PascalCase
# `type`/`interface`/`enum`/`model X` and `export const XSchema` (Zod).
decls=$(printf '%s\n' "$added" \
  | grep -oE '\b(type|interface|enum|model)[[:space:]]+[A-Z][A-Za-z0-9_]*' \
  | awk '{print $2}' || true)
schemas=$(printf '%s\n' "$added" \
  | grep -oE '\bexport[[:space:]]+const[[:space:]]+[A-Z][A-Za-z0-9_]*Schema\b' \
  | awk '{print $NF}' | sed 's/Schema$//' || true)

# Drop common implementation suffixes — these are plumbing, not domain nouns.
candidates=$(printf '%s\n%s\n' "$decls" "$schemas" | sed '/^$/d' | sort -u \
  | grep -vE '(Props|State|Args|Input|Output|Response|Request|Dto|Config|Options|Context|Provider|Handler|Params|Ref|Event|Error)$' || true)
[ -z "$candidates" ] && exit 0

# Keep only candidates absent from every KNOWLEDGE*.md in the repo.
undocumented=""
for c in $candidates; do
  if ! grep -rqiw --include='KNOWLEDGE*.md' --exclude-dir=node_modules "$c" "$repo" 2>/dev/null; then
    undocumented="$undocumented $c"
  fi
done
undocumented=$(printf '%s' "$undocumented" | sed 's/^ *//')
[ -z "$undocumented" ] && exit 0

# New, undocumented domain type(s) on the branch → nudge once.
: > "$marker"

reason="This branch introduced type(s) not found in any KNOWLEDGE*.md: ${undocumented}. If any are real domain terms, add them to the glossary following commands/update-knowledge.md (the same procedure /update-knowledge runs). If they are implementation types (props, DTOs, UI state) or already covered under another name, make NO edits and produce NO user-facing summary — just stop. Do not print a reconciliation table."

jq -n --arg r "$reason" '{decision: "block", reason: $r}'
exit 0
