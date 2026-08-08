# Claude-specific rules

Shared rules live in `shared/agent-rules.md`, loaded via the `~/code/CLAUDE.md` symlink.
This file holds only what is specific to Claude Code.

## Github interactions

- **Prefer the GitHub MCP server** (`mcp__github__*` tools) for all GitHub operations: PR create/edit, issue create/edit, commenting, reviewing, reading PR/issue state, status checks, etc. JSON-typed args mean no shell-quoting hazards (markdown backticks in PR bodies stay literal), tool calls parallelize within a single message, and a single `pull_request_read` returns mergeable state + checks + stats in one shot.
- **Fall back to the `gh` CLI** only when (a) the MCP doesn't expose the operation you need, (b) the MCP fails, or (c) you genuinely need an interactive flow. When using `gh` for multi-line content (PR body, issue body, commit message), write the body to `/tmp/<purpose>.txt` with the Write tool and pass `--body-file` / `-F` — never use `"$(cat <<'EOF' ... EOF)"`, since markdown backticks have leaked through quoted heredocs and triggered real command substitution (one historical case actually ran `vercel deploy --prod` from a PR body).
