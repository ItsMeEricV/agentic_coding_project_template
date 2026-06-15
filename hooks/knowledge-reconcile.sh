#!/usr/bin/env bash
# Stop hook — nudges the agent to reconcile KNOWLEDGE.md when a session
# looks like it pinned down domain language but never updated the glossary.
#
# This is the "dumb" first iteration: a fixed lexical grep over the session
# transcript for cue phrases. It is intentionally crude — tune PHRASES from
# real misses/false-alarms, or graduate to a git-diff signal later. It does
# NOT restate the reconcile procedure; it points the agent at the single
# source of truth in commands/update-knowledge.md (run as /update-knowledge).
#
# Fires (blocks the stop once) only when ALL hold:
#   - a KNOWLEDGE.md / KNOWLEDGE-MAP.md exists in the repo
#   - the transcript matches a cue phrase
#   - no KNOWLEDGE*.md was already modified in the working tree this session
#     (if the agent maintained it inline, there's nothing to nag about)
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

transcript=$(printf '%s' "$input" | jq -r '.transcript_path // empty')
session_id=$(printf '%s' "$input" | jq -r '.session_id // empty')
cwd=$(printf '%s' "$input" | jq -r '.cwd // empty')
[ -z "$transcript" ] || [ ! -f "$transcript" ] && exit 0
[ -z "$cwd" ] && exit 0

repo=$(git -C "$cwd" rev-parse --show-toplevel 2>/dev/null || true)
[ -z "$repo" ] && exit 0

# Only nag repos that already keep a glossary.
glossary=""
for f in KNOWLEDGE.md KNOWLEDGE-MAP.md; do
  [ -f "$repo/$f" ] && glossary="$repo/$f" && break
done
[ -z "$glossary" ] && exit 0

# Once-per-session marker.
marker="${TMPDIR:-/tmp}/claude-knowledge-reconcile-${session_id:-nosession}.done"
[ -f "$marker" ] && exit 0

# If a KNOWLEDGE*.md is already dirty in the working tree, assume the agent
# maintained it inline this session — nothing to nudge about.
if git -C "$repo" status --porcelain 2>/dev/null | grep -qiE 'KNOWLEDGE[A-Z-]*\.md$'; then
  exit 0
fi

# --- Dumb lexical signal -----------------------------------------------------
# First-pass cue phrases. Deliberately conservative-ish; expect to tune.
# Phrases avoid apostrophes on purpose ("call it" matches let's/we'll/we call
# it) so detection needs no Unicode normalization. LC_ALL=C keeps grep happy on
# arbitrary transcript bytes.
PHRASES='call it|name it|refers to|is defined as|we define|the term|canonical term|disambiguate|glossary|rename|deep-discuss'

if ! LC_ALL=C grep -qiE "$PHRASES" "$transcript"; then
  exit 0
fi

# Signal present and glossary untouched → nudge once.
: > "$marker"

reason=$(cat <<'EOF'
This session appears to have discussed or pinned down domain terms, but no KNOWLEDGE*.md was updated. Before finishing, reconcile the project glossary: follow the procedure in commands/update-knowledge.md (the same one /update-knowledge runs) — list the domain terms that came up, mark each recorded/updated/missing, and write the gaps. If there is genuinely nothing new or changed to record, say so explicitly and then stop.
EOF
)

jq -n --arg r "$reason" '{decision: "block", reason: $r}'
exit 0
