#!/usr/bin/env bash
# SessionStart hook: shows the reviewer's catalog report to the user (systemMessage)
# and the session (additionalContext). A check that cannot run says so, so a broken
# check never reads as a quiet day. pi runs the same check through
# .pi/extensions/catalog-notice.ts.
set -u
root="${CLAUDE_PROJECT_DIR:-$PWD}"
[ -f "$root/cli/agent_code_reviewer.py" ] || exit 0

if ! command -v uv >/dev/null 2>&1; then
  printf '%s\n' '{"systemMessage": "Reviewer catalog check did not run: uv is not installed, so models newer than the roster go unreported."}'
  exit 0
fi

err=$(mktemp)
trap 'rm -f "$err"' EXIT
if report=$(uv run --quiet "$root/cli/agent_code_reviewer.py" --catalog-notice 2>"$err"); then
  [ -n "$report" ] || exit 0
else
  status=$?
  report="Reviewer catalog check failed (exit $status), so models newer than the roster go unreported: $(tail -n 3 "$err")"
fi

printf '%s' "$report" | uv run --quiet --no-project python -c '
import json, sys
m = sys.stdin.read()
print(json.dumps({"systemMessage": m, "hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": m}}))
' || printf '%s\n' '{"systemMessage": "Reviewer catalog check could not format its report; run: uv run cli/agent_code_reviewer.py --catalog-notice"}'
